import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.security import hash_access_token
from app.db.init_db import init_db
from app.db.models import AccessToken, CalendarConnection, MeetingCapture, User
from app.db.session import SessionLocal
from app.main import app


client = TestClient(app)


def create_authenticated_user():
    init_db()
    db = SessionLocal()
    for table in (MeetingCapture, CalendarConnection, AccessToken, User):
        db.execute(delete(table))
    db.commit()
    user = User(email="calendar@example.com")
    db.add(user)
    db.flush()
    token = "calendar-test-access-token"
    db.add(AccessToken(user_id=user.id, token_hash=hash_access_token(token)))
    db.commit()
    user_id = user.id
    db.close()
    return user_id, token


def test_create_calendar_connection_and_schedule_event(monkeypatch):
    import app.services.recall_capture_service as capture_service

    user_id, token = create_authenticated_user()
    monkeypatch.setattr(capture_service.settings, "recall_api_key", "test-recall-key")
    monkeypatch.setattr(capture_service.settings, "recall_api_base_url", "https://us-east-1.recall.ai/api/v1")

    async def create_calendar(self, payload):
        return {"id": "recall-calendar-1", "status": "connected", "platform_email": "user@example.com"}

    async def retrieve_calendar_event(self, event_id):
        return {
            "id": event_id,
            "title": "Planning session",
            "start_time": "2026-10-20T10:00:00Z",
            "end_time": "2026-10-20T10:30:00Z",
            "meeting_url": "https://meet.google.com/abc-defg-hij",
        }

    async def schedule_calendar_event_bot(self, event_id, payload=None):
        return {"event_id": event_id}

    monkeypatch.setattr(capture_service.RecallClient, "create_calendar", create_calendar)
    monkeypatch.setattr(capture_service.RecallClient, "retrieve_calendar_event", retrieve_calendar_event)
    monkeypatch.setattr(capture_service.RecallClient, "schedule_calendar_event_bot", schedule_calendar_event_bot)

    connection_response = client.post(
        "/api/integrations/recall/calendars",
        json={
            "platform": "google_calendar",
            "oauth_client_id": "client-id",
            "oauth_client_secret": "client-secret",
            "oauth_refresh_token": "refresh-token",
            "oauth_email": "user@example.com",
            "consent_confirmed": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert connection_response.status_code == 201
    connection_id = connection_response.json()["id"]

    schedule_response = client.post(
        f"/api/integrations/recall/calendars/{connection_id}/events/event-123/schedule",
        json={"consent_confirmed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert schedule_response.status_code == 200
    body = schedule_response.json()
    assert body["calendar_event_id"] == "event-123"
    assert body["title"] == "Planning session"
    assert body["status"] == "scheduled"

    db = SessionLocal()
    capture = db.query(MeetingCapture).filter_by(calendar_event_id="event-123").first()
    assert capture is not None
    assert capture.capture_source == "calendar"
    db.close()