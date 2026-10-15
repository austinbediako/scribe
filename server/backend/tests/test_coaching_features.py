from collections.abc import Iterator

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import (
    BehaviorObservation,
    Meeting,
    MicroAction,
    TranscriptSegment,
    User,
    WeeklyInsight,
)
from app.db.session import SessionLocal
from app.services.analysis_service import analyze_meeting
from app.services.insight_service import generate_weekly_insight_for_user


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    session.execute(delete(MicroAction))
    session.execute(delete(WeeklyInsight))
    session.execute(delete(BehaviorObservation))
    session.execute(delete(TranscriptSegment))
    session.execute(delete(Meeting))
    session.execute(delete(User))
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def add_meeting(db: Session, email: str, transcript: list[str]) -> Meeting:
    user = User(email=email)
    db.add(user)
    db.flush()

    meeting = Meeting(
        granola_meeting_id=f"granola-{email}",
        title="Leadership coaching test",
        user_id=user.id,
    )
    db.add(meeting)
    db.flush()

    for index, text in enumerate(transcript):
        db.add(
            TranscriptSegment(
                meeting_id=meeting.id,
                speaker_name="Leader",
                speaker_id="me",
                text=text,
                start_time_ms=index * 10000,
                end_time_ms=(index + 1) * 10000,
            )
        )
    db.commit()
    return meeting


def test_analysis_identifies_questions_instructions_and_recognition(db: Session) -> None:
    meeting = add_meeting(
        db,
        "leader@example.com",
        [
            "What do you think about the launch plan?",
            "I need you to own the follow-up.",
            "Thanks for the careful analysis.",
        ],
    )

    observations = analyze_meeting(db, meeting.id)
    by_label = {observation.behavior_label: observation for observation in observations}

    assert {"asks_open_questions", "gives_direct_instructions", "recognizes_contributions"} <= by_label.keys()
    assert by_label["asks_open_questions"].evidence_text == "What do you think about the launch plan?"
    assert by_label["gives_direct_instructions"].evidence_text == "I need you to own the follow-up."
    assert by_label["recognizes_contributions"].evidence_text == "Thanks for the careful analysis."
    assert all(observation.is_supported for observation in observations)


def test_analysis_marks_missing_behavior_signals_as_insufficient_evidence(db: Session) -> None:
    meeting = add_meeting(db, "leader@example.com", ["The meeting is scheduled for Thursday."])

    observations = analyze_meeting(db, meeting.id)

    assert len(observations) == 1
    assert observations[0].behavior_label == "insufficient_evidence"
    assert observations[0].is_supported is False
    assert observations[0].confidence == "low"


def test_weekly_insight_uses_only_the_requested_leaders_evidence(db: Session) -> None:
    first_meeting = add_meeting(db, "leader@example.com", [])
    second_meeting = add_meeting(db, "other-leader@example.com", [])
    db.add(
        BehaviorObservation(
            meeting_id=first_meeting.id,
            behavior_label="recognizes_contributions",
            evidence_text="Thanks for the careful analysis.",
            confidence="medium",
            is_supported=True,
        )
    )
    db.add(
        BehaviorObservation(
            meeting_id=second_meeting.id,
            behavior_label="gives_direct_instructions",
            evidence_text="Other leader's private transcript evidence.",
            confidence="medium",
            is_supported=True,
        )
    )
    db.commit()

    insight = generate_weekly_insight_for_user(db, user_email="leader@example.com")

    assert insight["status"] == "generated"
    assert insight["strength"].startswith("You make people feel seen")
    assert insight["growth_area"]
    assert insight["micro_action"]
    assert "Thanks for the careful analysis." in insight["evidence_summary"]
    assert "Other leader's private transcript evidence." not in insight["evidence_summary"]
    assert db.query(WeeklyInsight).count() == 1


def test_weekly_insight_is_idempotent_within_the_current_week(db: Session) -> None:
    meeting = add_meeting(db, "leader@example.com", [])
    db.add(
        BehaviorObservation(
            meeting_id=meeting.id,
            behavior_label="asks_open_questions",
            evidence_text="What do you think about the launch plan?",
            confidence="high",
            is_supported=True,
        )
    )
    db.commit()

    first = generate_weekly_insight_for_user(db, user_email="leader@example.com")
    second = generate_weekly_insight_for_user(db, user_email="leader@example.com")

    assert first["status"] == "generated"
    assert second["id"] == first["id"]
    assert second["micro_action_id"] == first["micro_action_id"]
    assert db.query(WeeklyInsight).count() == 1
    assert db.query(MicroAction).count() == 1


def test_current_insight_route_returns_a_coaching_card(db: Session) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    meeting = add_meeting(db, "demo@example.com", [])
    db.add(
        BehaviorObservation(
            meeting_id=meeting.id,
            behavior_label="asks_open_questions",
            evidence_text="What do you think about the launch plan?",
            confidence="high",
            is_supported=True,
        )
    )
    db.commit()

    client = TestClient(app)
    assert client.get("/api/insights/current").status_code in {401, 403}

    signup = client.post(
        "/api/auth/signup",
        json={"email": "demo@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    response = client.get("/api/insights/current", headers=headers)

    assert response.status_code == 200
    card = response.json()
    assert card["status"] == "generated"
    assert card["strength"]
    assert card["growth_area"]
    assert card["evidence_summary"]
    assert card["micro_action"]


def test_analysis_reports_talk_time_by_speaker(db: Session) -> None:
    meeting = add_meeting(db, "leader@example.com", ["One turn.", "Another turn."])
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    signup = client.post(
        "/api/auth/signup",
        json={"email": "leader@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    response = client.post(f"/api/meetings/{meeting.id}/analyze", headers=headers)

    assert response.status_code == 200
    assert response.json()["metrics"]["talk_time_ms_by_speaker"] == {"Leader": 20000}


def test_insight_list_requires_an_authenticated_owner(db: Session) -> None:
    db.add(
        WeeklyInsight(
            strength="Private leader insight",
            growth_area="Private growth area",
            evidence_summary="Private evidence",
            micro_action="Private action",
        )
    )
    db.commit()
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/api/insights")

    assert response.status_code in {401, 403}


def test_completing_micro_action_persists_its_status(db: Session) -> None:
    user = User(email="leader@example.com")
    db.add(user)
    db.flush()
    insight = WeeklyInsight(
        user_id=user.id,
        strength="Strength",
        growth_area="Growth area",
        evidence_summary="Evidence",
        micro_action="Ask one teammate for a different perspective.",
    )
    db.add(insight)
    db.flush()
    action = MicroAction(insight_id=insight.id, title=insight.micro_action, status="planned")
    db.add(action)
    db.commit()
    action_id = action.id

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    signup = client.post(
        "/api/auth/signup",
        json={"email": "leader@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    unauthenticated = client.patch(f"/api/actions/{action_id}")
    assert unauthenticated.status_code in {401, 403}

    other = client.post(
        "/api/auth/signup",
        json={"email": "other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    forbidden = client.patch(f"/api/actions/{action_id}", headers=other_headers)
    assert forbidden.status_code == 404

    response = client.patch(f"/api/actions/{action_id}", headers=headers)
    db.expire_all()

    assert response.status_code == 200
    assert db.get(MicroAction, action_id).status == "completed"
