from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Meeting, TranscriptSegment, User


class GranolaClient:
    NOTES_PAGE_SIZE = 30
    TRANSCRIPT_PAGE_SIZE = 100

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        demo_mode: bool | None = None,
    ):
        self.api_key = settings.granola_api_key if api_key is None else api_key
        self.base_url = (settings.granola_api_base_url if base_url is None else base_url).rstrip("/")
        self.demo_mode = settings.should_use_demo_data if demo_mode is None else demo_mode
        self._request_lock = asyncio.Lock()
        self._last_request_at: float | None = None

        if not self.demo_mode:
            self._validate_production_configuration()

        auth_value = f"{settings.granola_auth_scheme} {self.api_key}".strip()
        self.headers = {
            settings.granola_auth_header: auth_value,
            "Accept": "application/json",
        }

    def _validate_production_configuration(self) -> None:
        placeholder_values = {"", "demo-key", "replace-me", "changeme", "example", "demo"}
        if self.api_key.lower() in placeholder_values:
            raise ValueError("Granola API credentials are required when demo mode is disabled.")
        if not self.base_url.startswith("https://") or ".example.com" in self.base_url:
            raise ValueError("A valid Granola API base URL is required when demo mode is disabled.")

    @property
    def is_demo_mode(self) -> bool:
        return self.demo_mode

    async def _pace_request(self) -> None:
        async with self._request_lock:
            now = time.monotonic()
            if self._last_request_at is not None:
                wait_time = 0.2 - (now - self._last_request_at)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self._last_request_at = time.monotonic()

    async def list_notes_page(
        self,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], bool, str | None]:
        if self.is_demo_mode:
            return demo_meeting_payloads(), False, None

        async with httpx.AsyncClient(timeout=30.0) as client:
            params: dict[str, Any] = {"page_size": self.NOTES_PAGE_SIZE}
            if cursor:
                params["cursor"] = cursor
            await self._pace_request()
            response = await client.get(
                f"{self.base_url}/notes",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return extract_note_page(response.json())

    async def get_note(self, note_id: str, include_transcript: bool = True) -> dict[str, Any]:
        if self.is_demo_mode:
            return demo_meeting_payloads()[0]

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"include": "transcript"} if include_transcript else None
            await self._pace_request()
            response = await client.get(
                f"{self.base_url}/notes/{note_id}",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Granola Get Note returned a non-object response.")
            return payload

    async def get_transcript_page(
        self,
        note_id: str,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], bool, str | None]:
        if self.is_demo_mode:
            return demo_transcript_segments(), False, None

        async with httpx.AsyncClient(timeout=30.0) as client:
            params: dict[str, Any] = {"page_size": self.TRANSCRIPT_PAGE_SIZE}
            if cursor:
                params["cursor"] = cursor
            await self._pace_request()
            response = await client.get(
                f"{self.base_url}/notes/{note_id}/transcript",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return extract_transcript_page(response.json())


def demo_transcript_segments() -> list[dict[str, Any]]:
    return [
        {
            "speaker_name": "Ava",
            "text": "Thanks for sharing, I appreciate the progress on the launch plan.",
            "start_time_ms": 0,
            "end_time_ms": 4000,
        },
        {
            "speaker_name": "Ava",
            "text": "What do you think we should do if the timeline slips?",
            "start_time_ms": 5000,
            "end_time_ms": 9000,
        },
        {
            "speaker_name": "Alex",
            "text": "I need you to keep the team focused on the milestone and we should ship on Friday.",
            "start_time_ms": 10000,
            "end_time_ms": 14500,
        },
        {
            "speaker_name": "Alex",
            "text": "Let's hear from the rest of the team before we lock this in.",
            "start_time_ms": 15000,
            "end_time_ms": 18500,
        },
        {
            "speaker_name": "Ava",
            "text": "Great work on clarifying the risks, and I’d like to hear other options before we decide.",
            "start_time_ms": 19000,
            "end_time_ms": 23500,
        },
    ]


def demo_meeting_payloads() -> list[dict[str, Any]]:
    return [
        {
            "id": "granola-demo-meeting",
            "title": "Leadership sync demo",
            "started_at": "2026-10-14T09:00:00Z",
            "ended_at": "2026-10-14T09:30:00Z",
            "url": "https://granola.example.com/demo",
            "transcript": {"segments": demo_transcript_segments()},
        }
    ]


def _as_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _extract_page(
    payload: Any,
    collection_key: str,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    if not isinstance(payload, dict) or not isinstance(payload.get(collection_key), list):
        raise ValueError(f"Granola response must contain a '{collection_key}' array.")
    if not isinstance(payload.get("hasMore"), bool):
        raise ValueError("Granola paginated response must contain a boolean 'hasMore'.")

    cursor = payload.get("cursor")
    if cursor is not None and not isinstance(cursor, str):
        raise ValueError("Granola pagination cursor must be a string or null.")
    has_more = payload["hasMore"]
    if has_more and not cursor:
        raise ValueError("Granola returned hasMore=true without a continuation cursor.")

    items = [item for item in payload[collection_key] if isinstance(item, dict)]
    return items, has_more, cursor


def extract_note_page(payload: Any) -> tuple[list[dict[str, Any]], bool, str | None]:
    return _extract_page(payload, "notes")


def extract_transcript_page(payload: Any) -> tuple[list[dict[str, Any]], bool, str | None]:
    return _extract_page(payload, "transcript")


def _timestamp_to_milliseconds(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    parsed = _as_datetime(value)
    return int(parsed.timestamp() * 1000) if parsed is not None else None


def normalize_granola_note(payload: dict[str, Any]) -> dict[str, Any]:
    calendar_event = payload.get("calendar_event")
    if not isinstance(calendar_event, dict):
        calendar_event = {}

    transcript_segments = _extract_transcript_segments(payload)
    return {
        "id": payload.get("id") or "unknown-note-id",
        "title": payload.get("title") or "Untitled meeting",
        "started_at": (
            calendar_event.get("scheduled_start_time")
            or payload.get("started_at")
            or payload.get("start_time")
            or payload.get("created_at")
        ),
        "ended_at": (
            calendar_event.get("scheduled_end_time")
            or payload.get("ended_at")
            or payload.get("end_time")
        ),
        "url": payload.get("web_url") or payload.get("url") or payload.get("source_url") or "",
        "source": "granola",
        "transcript_available": bool(transcript_segments),
        "transcript_segments": transcript_segments,
    }


def _extract_transcript_segments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    transcript = payload.get("transcript", payload)
    if isinstance(transcript, dict):
        segments = transcript.get("segments") or transcript.get("utterances") or transcript.get("messages") or []
    else:
        segments = transcript if isinstance(transcript, list) else []

    cleaned: list[dict[str, Any]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue

        text = segment.get("text") or segment.get("content") or segment.get("transcript")
        if not text:
            continue

        speaker = segment.get("speaker")
        if not isinstance(speaker, dict):
            speaker = {}

        start_time = segment.get("start_time")
        end_time = segment.get("end_time")
        cleaned.append(
            {
                "speaker_name": (
                    speaker.get("name")
                    or speaker.get("diarization_label")
                    or speaker.get("attribution")
                    or segment.get("speaker_name")
                    or segment.get("speakerId")
                ),
                "speaker_id": (
                    speaker.get("attribution")
                    or speaker.get("diarization_label")
                    or speaker.get("source")
                    or segment.get("speaker_id")
                    or segment.get("speakerId")
                ),
                "text": str(text),
                "start_time_ms": (
                    _timestamp_to_milliseconds(start_time)
                    if start_time is not None
                    else segment.get("start_time_ms") or segment.get("start_ms") or 0
                ),
                "end_time_ms": (
                    _timestamp_to_milliseconds(end_time)
                    if end_time is not None
                    else segment.get("end_time_ms") or segment.get("end_ms") or 0
                ),
            }
        )
    return cleaned


def upsert_meeting_from_payload(db: Session, user: User, payload: dict[str, Any]) -> Meeting:
    normalized = normalize_granola_note(payload)
    granola_meeting_id = normalized["id"]
    meeting = db.query(Meeting).filter_by(granola_meeting_id=granola_meeting_id).first()

    if meeting is None:
        meeting = Meeting(
            granola_meeting_id=granola_meeting_id,
            user_id=user.id,
        )
        db.add(meeting)
        db.flush()

    meeting.title = normalized["title"] or meeting.title or "Untitled meeting"
    meeting.started_at = _as_datetime(normalized.get("started_at")) or meeting.started_at
    meeting.ended_at = _as_datetime(normalized.get("ended_at")) or meeting.ended_at
    meeting.source_url = normalized.get("url") or meeting.source_url
    meeting.raw_payload = payload
    db.add(meeting)
    db.flush()

    segments = normalized.get("transcript_segments", [])
    for segment in segments:
        existing_segment = (
            db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.meeting_id == meeting.id,
                TranscriptSegment.text == segment["text"],
                TranscriptSegment.speaker_name == segment["speaker_name"],
            )
            .first()
        )
        if existing_segment is not None:
            continue

        db.add(
            TranscriptSegment(
                meeting_id=meeting.id,
                speaker_name=segment.get("speaker_name"),
                speaker_id=segment.get("speaker_id"),
                text=segment["text"],
                start_time_ms=segment.get("start_time_ms"),
                end_time_ms=segment.get("end_time_ms"),
            )
        )

    db.commit()
    db.refresh(meeting)
    return meeting


async def sync_meetings_for_user(db: Session, user_email: str = "demo@example.com") -> dict[str, Any]:
    user = db.query(User).filter_by(email=user_email).first()
    if user is None:
        user = User(email=user_email, granola_user_id="granola-demo-user")
        db.add(user)
        db.commit()
        db.refresh(user)

    client = GranolaClient()
    if settings.should_use_demo_data:
        note_payloads = demo_meeting_payloads()
    else:
        note_payloads = []
        cursor = None
        seen_cursors: set[str] = set()
        while True:
            page_notes, has_more, next_cursor = await client.list_notes_page(cursor=cursor)
            note_payloads.extend(page_notes)
            if not has_more:
                break
            if next_cursor in seen_cursors:
                raise RuntimeError("Granola pagination returned a repeated cursor.")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    synced_count = 0
    for listed_note in note_payloads:
        payload = listed_note
        if not settings.should_use_demo_data:
            note_id = listed_note.get("id")
            if not isinstance(note_id, str) or not note_id:
                continue
            try:
                payload = await client.get_note(note_id, include_transcript=True)
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 413:
                    raise
                payload = listed_note.copy()
                transcript_items: list[dict[str, Any]] = []
                transcript_cursor = None
                seen_transcript_cursors: set[str] = set()
                while True:
                    page_items, has_more, next_cursor = await client.get_transcript_page(
                        note_id,
                        cursor=transcript_cursor,
                    )
                    transcript_items.extend(page_items)
                    if not has_more:
                        break
                    if next_cursor in seen_transcript_cursors:
                        raise RuntimeError("Granola transcript pagination returned a repeated cursor.")
                    seen_transcript_cursors.add(next_cursor)
                    transcript_cursor = next_cursor
                payload["transcript"] = transcript_items

        if not settings.should_use_demo_data and payload.get("transcript") is None:
            transcript_items = []
            transcript_cursor = None
            seen_transcript_cursors = set()
            while True:
                page_items, has_more, next_cursor = await client.get_transcript_page(
                    payload["id"],
                    cursor=transcript_cursor,
                )
                transcript_items.extend(page_items)
                if not has_more:
                    break
                if next_cursor in seen_transcript_cursors:
                    raise RuntimeError("Granola transcript pagination returned a repeated cursor.")
                seen_transcript_cursors.add(next_cursor)
                transcript_cursor = next_cursor
            payload["transcript"] = transcript_items

        normalized = normalize_granola_note(payload)
        meeting_id = normalized["id"]
        if meeting_id == "unknown-note-id":
            continue

        existing = db.query(Meeting).filter_by(granola_meeting_id=meeting_id).first()
        if existing is None:
            synced_count += 1

        upsert_meeting_from_payload(db, user, payload)

    db.commit()
    return {
        "status": "success",
        "synced_count": synced_count,
        "message": "Granola sync completed.",
    }
