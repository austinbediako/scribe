import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.security import hash_access_token
from app.db.init_db import init_db
from app.db.models import (
    AccessToken,
    BehaviorObservation,
    Meeting,
    MeetingCapture,
    RecallWebhookEvent,
    TranscriptSegment,
    User,
    WeeklyInsight,
)
from app.db.session import SessionLocal
from app.main import app


client = TestClient(app)


def create_authenticated_user() -> tuple[int, str]:
    init_db()
    db = SessionLocal()
    db.execute(delete(TranscriptSegment))
    db.execute(delete(BehaviorObservation))
    db.execute(delete(WeeklyInsight))
    db.execute(delete(Meeting))
    db.execute(delete(RecallWebhookEvent))
    db.execute(delete(MeetingCapture))
    db.execute(delete(AccessToken))
    db.execute(delete(User))
    user = User(email="capture@example.com")
    db.add(user)
    db.flush()
    token = "recall-test-access-token"
    db.add(AccessToken(user_id=user.id, token_hash=hash_access_token(token)))
    db.commit()
    user_id = user.id
    db.close()
    return user_id, token


def capture_request(**overrides):
    payload = {
        "title": "Planning session",
        "meeting_url": "https://meet.google.com/abc-defg-hij",
        "join_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        "consent_confirmed": True,
    }
    payload.update(overrides)
    return payload


def test_recall_capture_requires_authentication():
    response = client.post("/api/integrations/recall/captures", json=capture_request())

    assert response.status_code == 401


def test_recall_capture_requires_explicit_consent():
    _, token = create_authenticated_user()

    response = client.post(
        "/api/integrations/recall/captures",
        json=capture_request(consent_confirmed=False),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "consent" in response.json()["detail"].lower()


def test_recall_capture_requires_supported_meeting_url():
    _, token = create_authenticated_user()

    response = client.post(
        "/api/integrations/recall/captures",
        json=capture_request(meeting_url="https://example.org/meeting"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_recall_capture_requires_future_join_time():
    _, token = create_authenticated_user()
    join_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    response = client.post(
        "/api/integrations/recall/captures",
        json=capture_request(join_at=join_at),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_schedules_recall_bot_and_scopes_capture_to_user(monkeypatch):
    import httpx
    import app.services.recall_capture_service as capture_service
    import app.api.routes.captures as capture_routes

    user_id, token = create_authenticated_user()
    monkeypatch.setattr(capture_service.settings, "recall_api_key", "test-recall-key")
    monkeypatch.setattr(capture_service.settings, "recall_api_base_url", "https://us-east-1.recall.ai/api/v1")
    requests = []

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            requests.append({"url": url, "headers": headers, "json": json})
            return httpx.Response(
                201,
                json={"id": "recall-bot-123", "status": {"code": "joining_call"}},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(capture_service.httpx, "AsyncClient", lambda timeout: MockAsyncClient())

    response = client.post(
        "/api/integrations/recall/captures",
        json=capture_request(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["title"] == "Planning session"
    assert body["consent_confirmed"] is True
    assert "meeting_url" not in body
    assert requests[0]["url"] == "https://us-east-1.recall.ai/api/v1/bot/"
    assert requests[0]["headers"]["Authorization"] == "Token test-recall-key"
    assert requests[0]["json"]["meeting_url"] == "https://meet.google.com/abc-defg-hij"
    assert requests[0]["json"]["metadata"]["scribe_capture_id"] == body["id"]
    assert "recording_config" not in requests[0]["json"]

    db = SessionLocal()
    capture = db.query(MeetingCapture).filter_by(id=int(body["id"])).first()
    assert capture is not None
    assert capture.user_id == user_id
    assert capture.recall_bot_id == "recall-bot-123"
    db.close()


def test_recall_bot_creation_retries_429_using_retry_after(monkeypatch):
    import asyncio
    import httpx
    import app.services.recall_capture_service as capture_service

    monkeypatch.setattr(capture_service.settings, "recall_api_key", "test-recall-key")
    monkeypatch.setattr(capture_service.settings, "recall_api_base_url", "https://us-east-1.recall.ai/api/v1")
    monkeypatch.setattr(capture_service.random, "uniform", lambda _minimum, _maximum: 0.25)
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(capture_service.asyncio, "sleep", fake_sleep)
    requests = []

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            requests.append((url, headers, json))
            if len(requests) == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "2"},
                    request=httpx.Request("POST", url),
                )
            return httpx.Response(
                201,
                json={"id": "retry-bot-id"},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(capture_service.httpx, "AsyncClient", lambda timeout: MockAsyncClient())
    capture = MeetingCapture(
        id=1,
        user_id=1,
        title="Retry test",
        meeting_url="https://meet.google.com/abc-defg-hij",
        join_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        consent_confirmed=True,
    )

    async def run():
        return await capture_service.RecallClient().schedule_capture(capture)

    result = asyncio.run(run())

    assert result["id"] == "retry-bot-id"
    assert len(requests) == 2
    assert delays == [2.25]


def test_recall_capture_is_disabled_without_server_key(monkeypatch):
    import app.services.recall_capture_service as capture_service

    _, token = create_authenticated_user()
    monkeypatch.setattr(capture_service.settings, "recall_api_key", "")

    response = client.post(
        "/api/integrations/recall/captures",
        json=capture_request(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.headers["X-Error-Code"] == "RECALL_NOT_CONFIGURED"


def test_recall_webhook_validates_signature_and_updates_capture(monkeypatch):
    import app.services.recall_capture_service as capture_service

    user_id, _ = create_authenticated_user()
    db = SessionLocal()
    capture = MeetingCapture(
        user_id=user_id,
        title="Planning session",
        meeting_url="https://meet.google.com/abc-defg-hij",
        join_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        consent_confirmed=True,
        recall_bot_id="recall-bot-123",
        status="scheduled",
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)
    capture_id = capture.id
    db.close()
    secret = "whsec_" + base64.b64encode(b"recall-webhook-secret").decode("ascii")
    monkeypatch.setattr(capture_service.settings, "recall_workspace_verification_secret", secret)

    event = {
        "event": "bot.status_change",
        "data": {
            "data": {"code": "bot.in_waiting_room", "sub_code": None, "updated_at": "2026-10-14T10:00:00Z"},
            "bot": {"id": "recall-bot-123", "metadata": {"scribe_capture_id": str(capture_id)}},
        },
    }
    raw_body = json.dumps(event, separators=(",", ":"))
    message_id = "msg-recall-test"
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    signed_content = f"{message_id}.{timestamp}.{raw_body}".encode()
    signature = base64.b64encode(hmac.new(b"recall-webhook-secret", signed_content, hashlib.sha256).digest()).decode()
    headers = {
        "webhook-id": message_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": f"v1,{signature}",
    }

    response = client.post("/api/webhooks/recall", content=raw_body, headers=headers)

    assert response.status_code == 200
    db = SessionLocal()
    saved_capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
    assert saved_capture.status == "waiting_room"
    db.close()


def test_recall_webhook_rejects_invalid_signature(monkeypatch):
    import app.services.recall_capture_service as capture_service

    monkeypatch.setattr(
        capture_service.settings,
        "recall_workspace_verification_secret",
        "whsec_" + base64.b64encode(b"recall-webhook-secret").decode("ascii"),
    )

    response = client.post(
        "/api/webhooks/recall",
        content="{}",
        headers={
            "webhook-id": "msg-invalid",
            "webhook-timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "webhook-signature": "v1,invalid",
        },
    )

    assert response.status_code == 401


def post_signed_recall_event(event, event_id):
    raw_body = json.dumps(event, separators=(",", ":"))
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    signed_content = f"{event_id}.{timestamp}.{raw_body}".encode()
    secret = b"recall-webhook-secret"
    signature = base64.b64encode(hmac.new(secret, signed_content, hashlib.sha256).digest()).decode()
    return client.post(
        "/api/webhooks/recall",
        content=raw_body,
        headers={
            "webhook-id": event_id,
            "webhook-timestamp": timestamp,
            "webhook-signature": f"v1,{signature}",
        },
    )


def test_recall_transcript_webhooks_import_and_analyze_meeting(monkeypatch):
    import app.services.recall_capture_service as capture_service

    user_id, _ = create_authenticated_user()
    monkeypatch.setattr(
        capture_service.settings,
        "recall_workspace_verification_secret",
        "whsec_" + base64.b64encode(b"recall-webhook-secret").decode("ascii"),
    )
    monkeypatch.setattr(capture_service.settings, "recall_api_key", "test-recall-key")
    db = SessionLocal()
    capture = MeetingCapture(
        user_id=user_id,
        title="Planning session",
        meeting_url="https://meet.google.com/abc-defg-hij",
        join_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        consent_confirmed=True,
        recall_bot_id="recall-bot-import",
        status="scheduled",
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)
    capture_id = capture.id
    db.close()

    transcript_requests = []

    async def create_async_transcript(self, recording_id):
        assert recording_id == "recall-recording-123"
        transcript_requests.append(recording_id)
        return {"id": "recall-transcript-456"}

    async def retrieve_transcript(self, transcript_id):
        assert transcript_id == "recall-transcript-456"
        return {"data": {"download_url": "https://download.example/transcript.json"}}

    async def download_transcript(self, download_url):
        assert download_url == "https://download.example/transcript.json"
        return [
            {
                "participant": {"id": 42, "name": "Alex"},
                "words": [
                    {
                        "text": "What do you think",
                        "start_timestamp": {"relative": 1.25},
                        "end_timestamp": {"relative": 2.5},
                    },
                    {
                        "text": "about this plan?",
                        "start_timestamp": {"relative": 2.6},
                        "end_timestamp": {"relative": 3.4},
                    },
                ],
            }
        ]

    monkeypatch.setattr(capture_service.RecallClient, "create_async_transcript", create_async_transcript)
    monkeypatch.setattr(capture_service.RecallClient, "retrieve_transcript", retrieve_transcript)
    monkeypatch.setattr(capture_service.RecallClient, "download_transcript", download_transcript)

    recording_event = {
        "event": "recording.done",
        "data": {
            "data": {"code": "done", "sub_code": None},
            "recording": {"id": "recall-recording-123", "metadata": {}},
            "bot": {
                "id": "recall-bot-import",
                "metadata": {"scribe_capture_id": str(capture_id)},
            },
        },
    }
    recording_response = post_signed_recall_event(recording_event, "msg-recording-done")
    assert recording_response.status_code == 200
    duplicate_recording_response = post_signed_recall_event(
        recording_event, "msg-recording-done-duplicate"
    )
    assert duplicate_recording_response.status_code == 200
    assert len(transcript_requests) == 1
    bot_done_event = {
        "event": "bot.status_change",
        "data": {
            "data": {"code": "bot.done", "sub_code": None},
            "bot": {
                "id": "recall-bot-import",
                "metadata": {"scribe_capture_id": str(capture_id)},
            },
        },
    }
    bot_done_response = post_signed_recall_event(bot_done_event, "msg-bot-done-late")
    assert bot_done_response.status_code == 200

    transcript_event = {
        "event": "transcript.done",
        "data": {
            "data": {"code": "done", "sub_code": None},
            "transcript": {"id": "recall-transcript-456", "metadata": {}},
            "recording": {"id": "recall-recording-123", "metadata": {}},
            "bot": {
                "id": "recall-bot-import",
                "metadata": {"scribe_capture_id": str(capture_id)},
            },
        },
    }
    transcript_response = post_signed_recall_event(transcript_event, "msg-transcript-done")
    assert transcript_response.status_code == 200

    db = SessionLocal()
    saved_capture = db.query(MeetingCapture).filter_by(id=capture_id).first()
    meeting = db.query(Meeting).filter_by(granola_meeting_id="recall:recall-bot-import").first()
    segments = db.query(TranscriptSegment).filter_by(meeting_id=meeting.id).all()
    observations = db.query(BehaviorObservation).filter_by(meeting_id=meeting.id).all()
    insight = db.query(WeeklyInsight).filter_by(meeting_id=meeting.id).first()
    assert saved_capture.recall_recording_id == "recall-recording-123"
    assert saved_capture.recall_transcript_id == "recall-transcript-456"
    assert saved_capture.status == "completed"
    assert saved_capture.meeting_id == meeting.id
    assert meeting.user_id == user_id
    assert meeting.title == "Planning session"
    assert len(segments) == 1
    assert segments[0].speaker_name == "Alex"
    assert segments[0].speaker_id == "42"
    assert segments[0].text == "What do you think about this plan?"
    assert segments[0].start_time_ms == 1250
    assert segments[0].end_time_ms == 3400
    assert any(item.behavior_label == "asks_open_questions" for item in observations)
    assert insight is not None
    db.close()
