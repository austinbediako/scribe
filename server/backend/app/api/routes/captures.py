from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.db.models import CalendarConnection, MeetingCapture, User
from app.services.recall_capture_service import (
    RecallClient,
    RecallNotConfiguredError,
    accept_recording_event,
    accept_transcript_event,
    apply_recall_status_event,
    broadcast_capture_status,
    process_recall_transcript,
    start_recall_transcription,
    unschedule_calendar_capture_for_user,
    verify_recall_signature,
)

router = APIRouter()
SUPPORTED_HOSTS = ("meet.google.com", "zoom.us", "teams.microsoft.com", "teams.live.com", "webex.com")


class CaptureRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    meeting_url: HttpUrl
    join_at: datetime | None = None
    consent_confirmed: bool

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Meeting title is required.")
        return value

    @field_validator("meeting_url")
    @classmethod
    def meeting_url_must_be_supported(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlsplit(str(value))
        hostname = (parsed.hostname or "").lower()
        is_supported = any(hostname == host or hostname.endswith(f".{host}") for host in SUPPORTED_HOSTS)
        if parsed.scheme != "https" or not is_supported:
            raise ValueError("Use a Google Meet, Zoom, Microsoft Teams, or Webex meeting URL.")
        return value

    @field_validator("join_at")
    @classmethod
    def meeting_must_be_scheduled_in_advance(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Meeting start time must include a timezone.")
        if value.astimezone(timezone.utc) < datetime.now(timezone.utc):
            raise ValueError("Meeting start time must be in the future.")
        return value.astimezone(timezone.utc)


def _serialize_capture(capture: MeetingCapture) -> dict[str, Any]:
    return {
        "id": str(capture.id),
        "title": capture.title,
        "join_at": capture.join_at.isoformat(),
        "consent_confirmed": capture.consent_confirmed,
        "status": capture.status,
        "status_detail": capture.status_detail,
        "meeting_id": str(capture.meeting_id) if capture.meeting_id is not None else None,
        "created_at": capture.created_at.isoformat(),
    }


@router.post("/api/integrations/recall/captures", status_code=status.HTTP_201_CREATED)
async def create_capture(
    payload: CaptureRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payload.consent_confirmed:
        raise HTTPException(status_code=400, detail="Confirm consent and permission to capture this meeting.")
    if not settings.recall_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recall meeting capture is not configured.",
            headers={"X-Error-Code": "RECALL_NOT_CONFIGURED"},
        )

    scheduled_join_at = payload.join_at or (datetime.now(timezone.utc) + timedelta(minutes=1))
    capture = MeetingCapture(
        user_id=user.id,
        title=payload.title,
        meeting_url=str(payload.meeting_url),
        join_at=scheduled_join_at,
        consent_confirmed=True,
        status="scheduling",
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    try:
        recall_bot = await RecallClient().schedule_capture(capture)
    except RecallNotConfiguredError as exc:
        capture.status = "failed"
        capture.status_detail = "Recall is not configured."
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc), headers={"X-Error-Code": "RECALL_NOT_CONFIGURED"}) from exc
    except (httpx.HTTPError, ValueError) as exc:
        capture.status = "failed"
        capture.status_detail = "Recall could not schedule this capture."
        db.commit()
        raise HTTPException(status_code=502, detail="Recall could not schedule this capture.") from exc

    capture.recall_bot_id = recall_bot["id"]
    capture.status = "scheduled"
    initial_status = recall_bot.get("status")
    if isinstance(initial_status, dict):
        capture.status_detail = initial_status.get("code")
    db.commit()
    db.refresh(capture)
    return _serialize_capture(capture)


@router.get("/api/integrations/recall/captures")
def list_captures(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    captures = (
        db.query(MeetingCapture)
        .filter(MeetingCapture.user_id == user.id)
        .order_by(MeetingCapture.join_at.asc())
        .all()
    )
    return [_serialize_capture(capture) for capture in captures]


@router.delete("/api/integrations/recall/captures/{capture_id}")
async def cancel_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    capture = (
        db.query(MeetingCapture)
        .filter(MeetingCapture.id == capture_id, MeetingCapture.user_id == user.id)
        .first()
    )
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found.")
    if capture.status != "scheduled":
        raise HTTPException(status_code=409, detail="Only scheduled captures can be cancelled.")
    if not settings.recall_api_key:
        raise HTTPException(status_code=503, detail="Recall meeting capture is not configured.")

    try:
        if capture.capture_source == "calendar" or capture.calendar_event_id:
            await unschedule_calendar_capture_for_user(db, user, capture.id)
            db.refresh(capture)
        else:
            if not capture.recall_bot_id:
                raise HTTPException(status_code=409, detail="Only scheduled captures can be cancelled.")
            await RecallClient().cancel_scheduled_capture(capture.recall_bot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Recall could not cancel this capture.") from exc

    capture.status = "cancelled"
    capture.status_detail = "Cancelled by the Scribe user."
    db.commit()
    return _serialize_capture(capture)


@router.post("/api/webhooks/recall")
async def recall_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    webhook_id: str | None = Header(default=None, alias="webhook-id"),
    webhook_timestamp: str | None = Header(default=None, alias="webhook-timestamp"),
    webhook_signature: str | None = Header(default=None, alias="webhook-signature"),
):
    if not settings.recall_workspace_verification_secret:
        raise HTTPException(status_code=503, detail="Recall webhook verification is not configured.")

    raw_body = await request.body()
    if not verify_recall_signature(
        settings.recall_workspace_verification_secret,
        webhook_id,
        webhook_timestamp,
        webhook_signature,
        raw_body,
    ):
        raise HTTPException(status_code=401, detail="Invalid Recall webhook signature.")

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")

    event_type = payload.get("event")
    if not isinstance(event_type, str):
        return {"status": "ignored"}

    event_data = payload.get("data")
    calendar_id = event_data.get("calendar_id") if isinstance(event_data, dict) else None
    if event_type in {"calendar.update", "calendar.sync_events"}:
        if isinstance(calendar_id, str):
            connection = db.query(CalendarConnection).filter_by(recall_calendar_id=calendar_id).first()
            if connection is not None:
                try:
                    calendar = await RecallClient().retrieve_calendar(calendar_id)
                    connection.status = calendar.get("status", connection.status)
                    connection.platform_email = calendar.get("platform_email") or connection.platform_email
                    connection.status_detail = None
                    db.add(connection)
                    db.commit()
                except Exception:
                    pass
        return {"status": "accepted", "calendar_id": calendar_id}

    event_id = webhook_id or ""
    if event_type == "recording.done":
        capture, recording_id = accept_recording_event(db, event_id, payload)
        if capture is not None:
            background_tasks.add_task(broadcast_capture_status, capture.id)
        if recording_id:
            background_tasks.add_task(start_recall_transcription, capture.id, recording_id)
    elif event_type in {"transcript.done", "transcript.failed"}:
        capture, transcript_id = accept_transcript_event(db, event_id, event_type, payload)
        if capture is not None:
            background_tasks.add_task(broadcast_capture_status, capture.id)
        if transcript_id:
            background_tasks.add_task(process_recall_transcript, capture.id, transcript_id)
    else:
        capture = apply_recall_status_event(db, event_id, event_type, payload)
        if capture is not None:
            background_tasks.add_task(broadcast_capture_status, capture.id)
    if capture is None:
        return {"status": "ignored"}
    return {"status": "accepted", "capture_id": str(capture.id), "capture_status": capture.status}
