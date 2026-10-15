from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.models import (
    AccessToken,
    BehaviorObservation,
    CalendarConnection,
    Meeting,
    MeetingCapture,
    MicroAction,
    RecallWebhookEvent,
    TranscriptSegment,
    User,
    WeeklyInsight,
)
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "meeting_captures" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("meeting_captures")}
    new_columns = {
        "recall_recording_id": "VARCHAR(255)",
        "recall_transcript_id": "VARCHAR(255)",
        "meeting_id": "INTEGER",
        "calendar_connection_id": "INTEGER",
        "calendar_event_id": "VARCHAR(255)",
        "calendar_event_start_at": "DATETIME",
        "calendar_event_end_at": "DATETIME",
        "capture_source": "VARCHAR(50)",
    }
    with engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE meeting_captures ADD COLUMN {column_name} {column_type}")
                )
