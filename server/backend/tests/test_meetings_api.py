from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import Settings
from app.db.models import BehaviorObservation, Meeting, TranscriptSegment, User, WeeklyInsight
from app.db.session import SessionLocal
from app.main import app
from app.services.granola_sync_service import (
    GranolaClient,
    extract_note_page,
    extract_transcript_page,
    normalize_granola_note,
)


client = TestClient(app)


def reset_database():
    db = SessionLocal()
    db.execute(delete(WeeklyInsight))
    db.execute(delete(BehaviorObservation))
    db.execute(delete(TranscriptSegment))
    db.execute(delete(Meeting))
    db.execute(delete(User))
    db.commit()
    db.close()


def test_demo_mode_detection():
    settings = Settings(use_demo_data=True, granola_api_key="replace-me")
    assert settings.should_use_demo_data is True


def test_extracts_official_granola_notes_page():
    payload = {
        "notes": [
            {
                "id": "not_1d3tmYTlCICgjy",
                "title": "Weekly planning",
                "created_at": "2026-10-14T09:00:00Z",
                "updated_at": "2026-10-14T09:30:00Z",
                "web_url": "https://notes.granola.ai/d/123",
                "calendar_event": {
                    "scheduled_start_time": "2026-10-14T09:00:00Z",
                    "scheduled_end_time": "2026-10-14T09:30:00Z",
                },
            }
        ],
        "hasMore": True,
        "cursor": "cursor-2",
    }

    notes, has_more, cursor = extract_note_page(payload)
    normalized = normalize_granola_note(notes[0])

    assert len(notes) == 1
    assert has_more is True
    assert cursor == "cursor-2"
    assert normalized["id"] == "not_1d3tmYTlCICgjy"
    assert normalized["title"] == "Weekly planning"
    assert normalized["started_at"] == "2026-10-14T09:00:00Z"
    assert normalized["ended_at"] == "2026-10-14T09:30:00Z"
    assert normalized["url"] == "https://notes.granola.ai/d/123"


def test_normalizes_official_transcript_items():
    normalized = normalize_granola_note(
        {
            "id": "not_1d3tmYTlCICgjy",
            "title": "Weekly planning",
            "transcript": [
                {
                    "speaker": {"source": "speaker", "attribution": "them", "name": "Ava"},
                    "text": "What do you think?",
                    "start_time": "2026-10-14T09:00:00Z",
                    "end_time": "2026-10-14T09:00:07Z",
                }
            ],
        }
    )

    segment = normalized["transcript_segments"][0]
    assert segment["speaker_name"] == "Ava"
    assert segment["speaker_id"] == "them"
    assert segment["text"] == "What do you think?"
    assert segment["end_time_ms"] - segment["start_time_ms"] == 7000


def test_extracts_official_transcript_page():
    transcript, has_more, cursor = extract_transcript_page(
        {"transcript": [{"text": "Hello"}], "hasMore": True, "cursor": "transcript-2"}
    )

    assert transcript == [{"text": "Hello"}]
    assert has_more is True
    assert cursor == "transcript-2"


def test_production_client_rejects_placeholder_configuration():
    settings = Settings(
        use_demo_data=False,
        granola_api_key="replace-me",
        granola_api_base_url="https://api.granola.example.com",
    )

    try:
        GranolaClient(api_key=settings.granola_api_key, base_url=settings.granola_api_base_url, demo_mode=False)
    except ValueError as error:
        assert "Granola" in str(error)
    else:
        raise AssertionError("Production client accepted placeholder Granola configuration")


def test_granola_client_sends_configured_auth_and_cursor(monkeypatch):
    import asyncio

    import httpx
    import app.services.granola_sync_service as sync_service

    requests = []

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers, params):
            requests.append({"url": url, "headers": headers, "params": params})
            return httpx.Response(
                200,
                json={"notes": [{"id": "not_1d3tmYTlCICgjy"}], "hasMore": True, "cursor": "cursor-2"},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr(sync_service.httpx, "AsyncClient", lambda timeout: MockAsyncClient())
    monkeypatch.setattr(sync_service.settings, "granola_auth_header", "X-API-Key")
    monkeypatch.setattr(sync_service.settings, "granola_auth_scheme", "")
    granola_client = GranolaClient(
        api_key="real-key",
        base_url="https://api.granola.test/v1",
        demo_mode=False,
    )

    notes, has_more, next_cursor = asyncio.run(granola_client.list_notes_page(cursor="cursor-1"))

    assert notes[0]["id"] == "not_1d3tmYTlCICgjy"
    assert has_more is True
    assert next_cursor == "cursor-2"
    assert requests[0]["url"] == "https://api.granola.test/v1/notes"
    assert requests[0]["params"] == {"page_size": 30, "cursor": "cursor-1"}
    assert requests[0]["headers"]["X-API-Key"] == "real-key"


def test_granola_client_uses_documented_note_and_transcript_endpoints(monkeypatch):
    import asyncio

    import httpx
    import app.services.granola_sync_service as sync_service

    requests = []

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers, params):
            requests.append({"url": url, "params": params})
            if url.endswith("/transcript"):
                body = {"transcript": [], "hasMore": False, "cursor": None}
            else:
                body = {"id": "not_1d3tmYTlCICgjy", "transcript": []}
            return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(sync_service.httpx, "AsyncClient", lambda timeout: MockAsyncClient())
    granola_client = GranolaClient(
        api_key="real-key",
        base_url="https://api.granola.test/v1",
        demo_mode=False,
    )

    async def fetch_note_and_transcript():
        note = await granola_client.get_note("not_1d3tmYTlCICgjy")
        transcript, has_more, cursor = await granola_client.get_transcript_page(
            "not_1d3tmYTlCICgjy",
            cursor="transcript-cursor",
        )
        return note, transcript, has_more, cursor

    note, transcript, has_more, cursor = asyncio.run(fetch_note_and_transcript())

    assert note["id"] == "not_1d3tmYTlCICgjy"
    assert transcript == []
    assert has_more is False
    assert cursor is None
    assert requests == [
        {
            "url": "https://api.granola.test/v1/notes/not_1d3tmYTlCICgjy",
            "params": {"include": "transcript"},
        },
        {
            "url": "https://api.granola.test/v1/notes/not_1d3tmYTlCICgjy/transcript",
            "params": {"page_size": 100, "cursor": "transcript-cursor"},
        },
    ]


def test_live_sync_follows_has_more_even_when_page_is_short(monkeypatch):
    import asyncio

    import app.services.granola_sync_service as sync_service

    reset_database()
    page_cursors = []

    class FakeGranolaClient:
        async def list_notes_page(self, cursor=None):
            page_cursors.append(cursor)
            if cursor is None:
                return ([{"id": "not_1d3tmYTlCICgjy", "title": "Planning"}], True, "next-page")
            return ([], False, None)

        async def get_note(self, note_id, include_transcript=True):
            return {
                "id": note_id,
                "title": "Planning",
                "transcript": [],
            }

    monkeypatch.setattr(sync_service.settings, "use_demo_data", False)
    monkeypatch.setattr(sync_service, "GranolaClient", FakeGranolaClient)
    db = SessionLocal()
    try:
        result = asyncio.run(sync_service.sync_meetings_for_user(db, user_email="live@example.com"))
    finally:
        db.close()

    assert page_cursors == [None, "next-page"]
    assert result["synced_count"] == 1


def test_live_sync_falls_back_to_paginated_transcript_after_413(monkeypatch):
    import asyncio

    import httpx
    import app.services.granola_sync_service as sync_service

    reset_database()
    transcript_cursors = []

    class FakeGranolaClient:
        async def list_notes_page(self, cursor=None):
            return ([{"id": "not_1d3tmYTlCICgjy", "title": "Planning"}], False, None)

        async def get_note(self, note_id, include_transcript=True):
            request = httpx.Request("GET", f"https://api.granola.ai/v1/notes/{note_id}")
            response = httpx.Response(413, json={"code": "TRANSCRIPT_TOO_LARGE"}, request=request)
            raise httpx.HTTPStatusError("Transcript too large", request=request, response=response)

        async def get_transcript_page(self, note_id, cursor=None):
            transcript_cursors.append(cursor)
            if cursor is None:
                return ([{"text": "First", "speaker": {"name": "Ava"}}], True, "transcript-next")
            return ([{"text": "Second", "speaker": {"name": "Ava"}}], False, None)

    monkeypatch.setattr(sync_service.settings, "use_demo_data", False)
    monkeypatch.setattr(sync_service, "GranolaClient", FakeGranolaClient)
    db = SessionLocal()
    try:
        asyncio.run(sync_service.sync_meetings_for_user(db, user_email="transcript@example.com"))
        meeting = db.query(Meeting).filter_by(granola_meeting_id="not_1d3tmYTlCICgjy").first()
        assert meeting is not None
        assert [segment.text for segment in meeting.transcript_segments] == ["First", "Second"]
    finally:
        db.close()

    assert transcript_cursors == [None, "transcript-next"]


def auth_headers(email="leader@example.com"):
    response = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_list_meetings_requires_authentication():
    reset_database()
    response = client.get("/api/meetings")
    assert response.status_code in {401, 403}


def test_list_meetings_returns_empty_list():
    reset_database()
    response = client.get("/api/meetings", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == []


def test_sync_and_analyze_workflow(monkeypatch):
    import app.services.granola_sync_service as sync_service

    monkeypatch.setattr(sync_service.settings, "use_demo_data", True)
    reset_database()
    headers = auth_headers("demo@example.com")
    sync_response = client.post("/api/integrations/granola/sync", headers=headers)
    assert sync_response.status_code == 200
    assert sync_response.json()["status"] == "success"

    meetings = client.get("/api/meetings", headers=headers)
    assert meetings.status_code == 200
    assert len(meetings.json()) >= 1

    meeting_id = meetings.json()[0]["id"]
    analysis_response = client.post(f"/api/meetings/{meeting_id}/analyze", headers=headers)
    assert analysis_response.status_code == 200
    assert analysis_response.json()["observation_count"] >= 1
