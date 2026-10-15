from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import random
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import CalendarConnection, Meeting, MeetingCapture, RecallWebhookEvent, TranscriptSegment
from app.db.session import SessionLocal


STATUS_MAP = {
    "bot.joining_call": "joining",
    "bot.in_waiting_room": "waiting_room",
    "bot.in_call_not_recording": "joined",
    "bot.recording_permission_allowed": "recording",
    "bot.recording_permission_denied": "recording_denied",
    "bot.in_call_recording": "recording",
    "bot.call_ended": "processing",
    "bot.done": "processing",
    "bot.fatal": "failed",
}


class RecallNotConfiguredError(RuntimeError):
    pass


class RecallClient:
    def __init__(self) -> None:
        self.base_url = settings.recall_api_base_url.rstrip("/")
        self.api_key = settings.recall_api_key

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        for attempt in range(1, 7):
            request = getattr(client, method.lower())
            kwargs: dict[str, Any] = {"headers": headers}
            if json is not None:
                kwargs["json"] = json
            if params is not None:
                kwargs["params"] = params
            response = await request(url, **kwargs)
            if response.status_code not in {429, 503, 507}:
                response.raise_for_status()
                return response
            if attempt == 6:
                response.raise_for_status()

            if response.status_code == 429:
                try:
                    retry_after = max(0.0, float(response.headers.get("Retry-After", "1")))
                except ValueError:
                    retry_after = 1.0
            else:
                retry_after = 10.0 if response.status_code == 503 else 30.0
            await asyncio.sleep(retry_after + random.uniform(0.0, 5.0))
        raise RuntimeError("Recall request retry loop exited unexpectedly.")

    async def schedule_capture(self, capture: MeetingCapture) -> dict[str, Any]:
        if not self.api_key:
            raise RecallNotConfiguredError("Recall meeting capture is not configured.")

        payload = {
            "meeting_url": capture.meeting_url,
            "join_at": _as_utc(capture.join_at).isoformat(),
            "bot_name": "Scribe Meeting Coach",
            "metadata": {
                "scribe_capture_id": str(capture.id),
                "scribe_user_id": str(capture.user_id),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "POST",
                f"{self.base_url}/bot/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
                json=payload,
            )
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("id"), str):
                raise ValueError("Recall create-bot response did not contain a bot ID.")
            return result

    async def cancel_scheduled_capture(self, bot_id: str) -> None:
        if not self.api_key:
            raise RecallNotConfiguredError("Recall meeting capture is not configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            await self._request_with_retry(
                client,
                "DELETE",
                f"{self.base_url}/bot/{bot_id}/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
            )

    @property
    def calendar_base_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/api/v1"):
            base = base[: -len("/api/v1")]
        return base.rstrip("/") + "/api/v2"

    async def create_calendar(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "POST",
                f"{self.calendar_base_url}/calendars/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
                json=payload,
            )
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("id"), str):
                raise ValueError("Recall calendar response did not contain an ID.")
            return result

    async def retrieve_calendar(self, calendar_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                f"{self.calendar_base_url}/calendars/{calendar_id}/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Recall calendar response was invalid.")
            return result

    async def list_calendar_events(
        self, calendar_id: str, updated_at_gte: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if updated_at_gte:
            params["updated_at__gte"] = updated_at_gte
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                f"{self.calendar_base_url}/calendars/{calendar_id}/calendar_events/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
                params=params or None,
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Recall calendar events response was invalid.")
            return result

    async def schedule_calendar_event_bot(self, event_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload if payload is not None else {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "POST",
                f"{self.calendar_base_url}/calendar-events/{event_id}/bot/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
                json=payload,
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Recall calendar event scheduling response was invalid.")
            return result

    async def retrieve_calendar_event(self, event_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                f"{self.calendar_base_url}/calendar-events/{event_id}/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Recall calendar event response was invalid.")
            return result

    async def unschedule_calendar_event_bot(self, event_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await self._request_with_retry(
                client,
                "DELETE",
                f"{self.calendar_base_url}/calendar-events/{event_id}/bot/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
            )

    async def create_async_transcript(self, recording_id: str) -> dict[str, Any]:
        if not self.api_key:
            raise RecallNotConfiguredError("Recall meeting capture is not configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "POST",
                f"{self.base_url}/recording/{recording_id}/create_transcript/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
                json={
                    "provider": {"recallai_async": {"language_code": "auto"}},
                    "diarization": {"use_separate_streams_when_available": True},
                },
            )
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("id"), str):
                raise ValueError("Recall create-transcript response did not contain a transcript ID.")
            return result

    async def retrieve_bot(self, bot_id: str) -> dict[str, Any]:
        if not self.api_key:
            raise RecallNotConfiguredError("Recall meeting capture is not configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                f"{self.base_url}/bot/{bot_id}/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Recall bot response was invalid.")
            return result

    async def retrieve_transcript(self, transcript_id: str) -> dict[str, Any]:
        if not self.api_key:
            raise RecallNotConfiguredError("Recall meeting capture is not configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                f"{self.base_url}/transcript/{transcript_id}/",
                headers={"Authorization": f"Token {self.api_key}", "Accept": "application/json"},
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Recall transcript response was invalid.")
            return result

    async def download_transcript(self, download_url: str) -> list[dict[str, Any]]:
        parsed_url = urlsplit(download_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("Recall returned an invalid transcript download URL.")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                download_url,
                headers={"Accept": "application/json"},
            )
            result = response.json()
            if not isinstance(result, list):
                raise ValueError("Recall transcript download was not a list of utterances.")
            return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def verify_recall_signature(
    secret: str,
    webhook_id: str | None,
    timestamp: str | None,
    signature_header: str | None,
    raw_body: bytes,
    now: float | None = None,
) -> bool:
    if not secret.startswith("whsec_") or not webhook_id or not timestamp or not signature_header:
        return False

    try:
        timestamp_seconds = int(timestamp)
        signing_key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
    except (ValueError, binascii.Error):
        return False

    current_time = time.time() if now is None else now
    if abs(current_time - timestamp_seconds) > 300:
        return False

    signed_content = b".".join(
        [webhook_id.encode("utf-8"), timestamp.encode("utf-8"), raw_body]
    )
    expected = hmac.new(signing_key, signed_content, hashlib.sha256).digest()

    for versioned_signature in signature_header.split(" "):
        version, separator, signature = versioned_signature.partition(",")
        if version != "v1" or not separator:
            continue
        try:
            supplied = base64.b64decode(signature, validate=True)
        except (ValueError, binascii.Error):
            continue
        if hmac.compare_digest(expected, supplied):
            return True
    return False


def apply_recall_status_event(
    db: Session,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> MeetingCapture | None:
    event_data = payload.get("data")
    if not isinstance(event_data, dict):
        return None

    status_data = event_data.get("data")
    status_code = status_data.get("code") if isinstance(status_data, dict) else None
    status_code = status_code if isinstance(status_code, str) else event_type
    mapped_status = STATUS_MAP.get(status_code)
    if mapped_status is None:
        return None

    capture = find_capture_for_event(db, payload)
    if capture is None:
        return None

    if not register_event(db, capture, event_id, status_code):
        return capture

    if capture.status in {"completed", "failed", "cancelled"} or (
        capture.status in {"requesting_transcript", "transcribing", "importing_transcript"}
        and mapped_status in {"joining", "waiting_room", "joined", "recording", "recording_denied", "processing"}
    ):
        db.commit()
        return capture

    detail = status_data.get("sub_code") if isinstance(status_data, dict) else None
    capture.status = mapped_status
    capture.status_detail = str(detail)[:255] if detail else status_code
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return capture


def find_capture_for_event(db: Session, payload: dict[str, Any]) -> MeetingCapture | None:
    event_data = payload.get("data")
    bot = event_data.get("bot") if isinstance(event_data, dict) else None
    if not isinstance(bot, dict):
        return None
    bot_id = bot.get("id")
    if isinstance(bot_id, str):
        capture = db.query(MeetingCapture).filter_by(recall_bot_id=bot_id).first()
        if capture is not None:
            return capture
    metadata = bot.get("metadata")
    capture_id = metadata.get("scribe_capture_id") if isinstance(metadata, dict) else None
    if isinstance(capture_id, str) and capture_id.isdigit():
        return db.query(MeetingCapture).filter_by(id=int(capture_id)).first()
    return None


def register_event(db: Session, capture: MeetingCapture, event_id: str, event_type: str) -> bool:
    if db.query(RecallWebhookEvent).filter_by(event_id=event_id).first() is not None:
        return False
    db.add(RecallWebhookEvent(event_id=event_id, capture_id=capture.id, event_type=event_type))
    return True


def accept_recording_event(
    db: Session, event_id: str, payload: dict[str, Any]
) -> tuple[MeetingCapture | None, str | None]:
    capture = find_capture_for_event(db, payload)
    event_data = payload.get("data")
    recording = event_data.get("recording") if isinstance(event_data, dict) else None
    recording_id = recording.get("id") if isinstance(recording, dict) else None
    if capture is None or not isinstance(recording_id, str):
        return None, None
    if not register_event(db, capture, event_id, "recording.done"):
        return capture, None
    if capture.recall_recording_id == recording_id and capture.status in {
        "requesting_transcript",
        "transcribing",
        "importing_transcript",
        "completed",
    }:
        db.commit()
        return capture, None
    capture.recall_recording_id = recording_id
    capture.status = "requesting_transcript"
    capture.status_detail = "Recording ready; requesting transcript."
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return capture, recording_id


def accept_transcript_event(
    db: Session, event_id: str, event_type: str, payload: dict[str, Any]
) -> tuple[MeetingCapture | None, str | None]:
    capture = find_capture_for_event(db, payload)
    event_data = payload.get("data")
    transcript = event_data.get("transcript") if isinstance(event_data, dict) else None
    transcript_id = transcript.get("id") if isinstance(transcript, dict) else None
    status_data = event_data.get("data") if isinstance(event_data, dict) else None
    if capture is None or not isinstance(transcript_id, str):
        return None, None
    if not register_event(db, capture, event_id, event_type):
        return capture, None
    if (
        capture.recall_transcript_id == transcript_id
        and capture.status in {"importing_transcript", "completed"}
    ):
        db.commit()
        return capture, None
    capture.recall_transcript_id = transcript_id
    if event_type == "transcript.done":
        capture.status = "importing_transcript"
        capture.status_detail = "Transcript ready; importing into Scribe."
    else:
        sub_code = status_data.get("sub_code") if isinstance(status_data, dict) else None
        capture.status = "failed"
        capture.status_detail = str(sub_code or "Recall transcription failed.")[:255]
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return capture, transcript_id if event_type == "transcript.done" else None


async def start_recall_transcription(capture_id: int, recording_id: str) -> None:
    db = SessionLocal()
    try:
        capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
        if capture is None or capture.status != "requesting_transcript":
            return
        transcript = await RecallClient().create_async_transcript(recording_id)
        capture.recall_transcript_id = transcript["id"]
        capture.status_detail = "Transcript processing by Recall."
        db.add(capture)
        db.commit()
        await broadcast_capture_status(capture_id)
    except Exception:
        db.rollback()
        capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
        if capture is not None:
            capture.status = "failed"
            capture.status_detail = "Could not start transcript processing."
            db.commit()
            await broadcast_capture_status(capture_id)
    finally:
        db.close()


def normalize_recall_transcript(utterances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments = []
    for utterance in utterances:
        if not isinstance(utterance, dict):
            continue
        words = utterance.get("words")
        if not isinstance(words, list):
            continue
        valid_words = [word for word in words if isinstance(word, dict) and isinstance(word.get("text"), str)]
        text = " ".join(word["text"].strip() for word in valid_words if word["text"].strip())
        if not text:
            continue
        start_values = [
            word.get("start_timestamp", {}).get("relative")
            for word in valid_words
            if isinstance(word.get("start_timestamp"), dict)
        ]
        end_values = [
            word.get("end_timestamp", {}).get("relative")
            for word in valid_words
            if isinstance(word.get("end_timestamp"), dict)
        ]
        starts = [value for value in start_values if isinstance(value, (int, float))]
        ends = [value for value in end_values if isinstance(value, (int, float))]
        participant = utterance.get("participant")
        participant = participant if isinstance(participant, dict) else {}
        participant_id = participant.get("id")
        segments.append(
            {
                "text": text,
                "speaker_name": participant.get("name"),
                "speaker_id": str(participant_id) if participant_id is not None else None,
                "start_time_ms": int(min(starts) * 1000) if starts else None,
                "end_time_ms": int(max(ends) * 1000) if ends else None,
            }
        )
    return segments


async def process_recall_transcript(capture_id: int, transcript_id: str) -> None:
    db = SessionLocal()
    try:
        capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
        if capture is None or capture.status != "importing_transcript":
            return
        artifact = await RecallClient().retrieve_transcript(transcript_id)
        data = artifact.get("data")
        download_url = data.get("download_url") if isinstance(data, dict) else None
        if not isinstance(download_url, str):
            raise ValueError("Recall transcript artifact did not contain a download URL.")
        utterances = await RecallClient().download_transcript(download_url)
        segments = normalize_recall_transcript(utterances)
        if not segments:
            raise ValueError("Recall transcript contained no usable speech segments.")

        meeting = (
            db.query(Meeting).filter_by(granola_meeting_id=f"recall:{capture.recall_bot_id}").first()
        )
        if meeting is None:
            meeting = Meeting(
                granola_meeting_id=f"recall:{capture.recall_bot_id}",
                title=capture.title,
                started_at=_as_utc(capture.join_at).replace(tzinfo=None),
                source_url=capture.meeting_url,
                user_id=capture.user_id,
            )
            db.add(meeting)
            db.flush()
        else:
            db.execute(delete(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id))

        for segment in segments:
            db.add(TranscriptSegment(meeting_id=meeting.id, **segment))
        capture.meeting_id = meeting.id
        db.add(capture)
        db.commit()

        from app.services.analysis_service import analyze_meeting
        from app.services.insight_service import generate_weekly_insight_for_user

        analyze_meeting(db, meeting.id)
        generate_weekly_insight_for_user(db, user_email=capture.user.email)
        capture.status = "completed"
        capture.status_detail = "Transcript imported and analyzed."
        db.add(capture)
        db.commit()
        await broadcast_capture_status(capture_id)
        await broadcast_meetings_update(capture.user_id)
    except Exception:
        db.rollback()
        capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
        if capture is not None:
            capture.status = "failed"
            capture.status_detail = "Could not import or analyze the transcript."
            db.commit()
            await broadcast_capture_status(capture_id)
    finally:
        db.close()


async def broadcast_capture_status(capture_id: int) -> None:
    db = SessionLocal()
    try:
        capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
        if capture is None:
            return
        update = {
            "id": str(capture.id),
            "title": capture.title,
            "join_at": capture.join_at.isoformat(),
            "consent_confirmed": capture.consent_confirmed,
            "status": capture.status,
            "status_detail": capture.status_detail,
            "meeting_id": str(capture.meeting_id) if capture.meeting_id is not None else None,
            "created_at": capture.created_at.isoformat(),
        }
        from app.api.routes.websocket import broadcast

        await broadcast(capture.user_id, {"type": "capture.updated", "capture": update})
    finally:
        db.close()


async def broadcast_meetings_update(user_id: int) -> None:
    db = SessionLocal()
    try:
        from app.api.routes.websocket import _serialize_meetings, broadcast

        meetings = await _serialize_meetings(db, user_id)
        await broadcast(user_id, {"type": "meetings.updated", "meetings": meetings})
    finally:
        db.close()


def serialize_calendar_connection(connection):
    return {
        "id": str(connection.id),
        "provider": connection.provider,
        "recall_calendar_id": connection.recall_calendar_id,
        "platform_email": connection.platform_email,
        "status": connection.status,
        "status_detail": connection.status_detail,
        "created_at": connection.created_at.isoformat(),
        "updated_at": connection.updated_at.isoformat(),
    }


async def connect_calendar_for_user(db, user, payload):
    provider = payload["platform"]
    create_payload = {
        "platform": provider,
        "oauth_client_id": payload["oauth_client_id"],
        "oauth_refresh_token": payload["oauth_refresh_token"],
        "metadata": {"scribe_user_id": str(user.id)},
    }
    if payload.get("oauth_client_secret"):
        create_payload["oauth_client_secret"] = payload["oauth_client_secret"]
    if payload.get("oauth_email"):
        create_payload["oauth_email"] = payload["oauth_email"]

    recall_calendar = await RecallClient().create_calendar(create_payload)
    connection = CalendarConnection(
        user_id=user.id,
        provider=provider,
        recall_calendar_id=recall_calendar["id"],
        platform_email=recall_calendar.get("platform_email") or payload.get("oauth_email"),
        status=recall_calendar.get("status", "connecting"),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def list_calendar_connections(db, user):
    return (
        db.query(CalendarConnection)
        .filter(CalendarConnection.user_id == user.id)
        .order_by(CalendarConnection.created_at.desc())
        .all()
    )


async def get_calendar_connection_events(db, user, connection_id, updated_at_gte=None):
    connection = (
        db.query(CalendarConnection)
        .filter(CalendarConnection.id == connection_id, CalendarConnection.user_id == user.id)
        .first()
    )
    if connection is None:
        raise ValueError("Calendar connection not found.")
    artifact = await RecallClient().list_calendar_events(
        connection.recall_calendar_id, updated_at_gte=updated_at_gte
    )
    results = artifact.get("results")
    if not isinstance(results, list):
        results = artifact.get("calendar_events")
    if not isinstance(results, list):
        results = []
    return [item for item in results if isinstance(item, dict)]


async def schedule_calendar_capture_for_user(db, user, connection_id, event_id, consent_confirmed):
    if not consent_confirmed:
        raise ValueError("Confirm consent and permission to capture this meeting.")

    connection = (
        db.query(CalendarConnection)
        .filter(CalendarConnection.id == connection_id, CalendarConnection.user_id == user.id)
        .first()
    )
    if connection is None:
        raise ValueError("Calendar connection not found.")

    event = await RecallClient().retrieve_calendar_event(event_id)
    starts_at = event.get("start_time") or event.get("start_at")
    ends_at = event.get("end_time") or event.get("end_at")
    title = event.get("title") or event.get("summary") or "Captured meeting"
    meeting_url = event.get("meeting_url") or event.get("meetingUrl") or ""

    scheduled = await RecallClient().schedule_calendar_event_bot(event_id)
    bot_id = None
    if isinstance(scheduled, dict):
        if isinstance(scheduled.get("bot"), dict):
            bot_id = scheduled["bot"].get("id")
        else:
            bot_id = scheduled.get("bot_id")
    if not isinstance(bot_id, str):
        bot_id = "calendar-event:%s" % event_id

    existing = (
        db.query(MeetingCapture)
        .filter_by(user_id=user.id, calendar_event_id=event_id)
        .first()
    )
    if existing is not None:
        capture = existing
    else:
        capture = MeetingCapture(
            user_id=user.id,
            title=str(title)[:500],
            meeting_url=str(meeting_url),
            join_at=_parse_iso(starts_at) or datetime.now(timezone.utc),
            consent_confirmed=True,
            recall_bot_id=bot_id,
            calendar_connection_id=connection.id,
            calendar_event_id=event_id,
            capture_source="calendar",
            status="scheduled",
        )
        db.add(capture)

    capture.title = str(title)[:500]
    capture.meeting_url = str(meeting_url)
    if starts_at:
        capture.join_at = _parse_iso(starts_at) or capture.join_at
    capture.calendar_event_start_at = _parse_iso(starts_at) or capture.calendar_event_start_at
    capture.calendar_event_end_at = _parse_iso(ends_at) or capture.calendar_event_end_at
    capture.recall_bot_id = bot_id
    capture.status = "scheduled"
    capture.status_detail = "Calendar event scheduled for capture."
    db.commit()
    db.refresh(capture)
    return capture


async def unschedule_calendar_capture_for_user(db, user, capture_id):
    capture = (
        db.query(MeetingCapture)
        .filter(MeetingCapture.id == capture_id, MeetingCapture.user_id == user.id)
        .first()
    )
    if capture is None:
        raise ValueError("Capture not found.")
    if capture.calendar_event_id:
        await RecallClient().unschedule_calendar_event_bot(capture.calendar_event_id)
    capture.status = "cancelled"
    capture.status_detail = "Cancelled by the Scribe user."
    db.commit()


def _parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
