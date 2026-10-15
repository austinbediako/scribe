from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class AccessToken(Base):
    __tablename__ = "access_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped["User"] = relationship(back_populates="access_tokens")

if TYPE_CHECKING:
    from app.db.models import Meeting


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    granola_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    meetings: Mapped[list["Meeting"]] = relationship(back_populates="user")
    access_tokens: Mapped[list["AccessToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    meeting_captures: Mapped[list["MeetingCapture"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    calendar_connections: Mapped[list["CalendarConnection"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class MeetingCapture(Base):
    __tablename__ = "meeting_captures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    meeting_url: Mapped[str] = mapped_column(Text, nullable=False)
    join_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consent_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recall_bot_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    recall_recording_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recall_transcript_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calendar_connection_id: Mapped[int | None] = mapped_column(ForeignKey("calendar_connections.id"), nullable=True)
    calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_event_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calendar_event_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capture_source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduling", nullable=False)
    status_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped[User] = relationship(back_populates="meeting_captures")
    calendar_connection: Mapped["CalendarConnection | None"] = relationship(back_populates="captures")


class RecallWebhookEvent(Base):
    __tablename__ = "recall_webhook_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("meeting_captures.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    recall_calendar_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    platform_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="connecting", nullable=False)
    status_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped[User] = relationship(back_populates="calendar_connections")
    captures: Mapped[list[MeetingCapture]] = relationship(back_populates="calendar_connection")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    granola_meeting_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped[User] = relationship(back_populates="meetings")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="meeting")
    observations: Mapped[list["BehaviorObservation"]] = relationship(back_populates="meeting")
    insights: Mapped[list["WeeklyInsight"]] = relationship(back_populates="meeting")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    speaker_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speaker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="transcript_segments")


class BehaviorObservation(Base):
    __tablename__ = "behavior_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    behavior_label: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    is_supported: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="observations")


class WeeklyInsight(Base):
    __tablename__ = "weekly_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id"), nullable=True)
    strength: Mapped[str] = mapped_column(Text, nullable=False)
    growth_area: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    micro_action: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    meeting: Mapped[Meeting | None] = relationship(back_populates="insights")


class MicroAction(Base):
    __tablename__ = "micro_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    insight_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="planned", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)