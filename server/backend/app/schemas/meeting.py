from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MeetingSummary(BaseModel):
    id: str
    title: str | None = None
    source: str = "granola"
    started_at: datetime | None = None
    ended_at: datetime | None = None


class MeetingDetail(MeetingSummary):
    raw_payload: dict[str, Any] | None = None
    transcript_available: bool = False
