from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import BehaviorObservation, Meeting, MicroAction, User, WeeklyInsight


LABEL_TO_STRENGTH = {
    "asks_open_questions": "You consistently ask good clarifying questions before moving to a decision.",
    "gives_direct_instructions": "You are clear and decisive when the team needs direction.",
    "recognizes_contributions": "You make people feel seen by recognizing progress and effort.",
    "invites_perspectives": "You actively bring people into the conversation and make space for their input.",
    "explores_alternatives": "You look for options and compare paths before deciding.",
    "insufficient_evidence": "There is not enough meeting evidence yet to make a confident claim.",
}

LABEL_TO_GROWTH = {
    "asks_open_questions": "You could balance questions with clearer decision framing so your team knows the next step.",
    "gives_direct_instructions": "You could invite more perspectives before closing a decision to increase buy-in.",
    "recognizes_contributions": "You could make recognition more specific and timely so it lands more strongly.",
    "invites_perspectives": "You could invite a broader range of voices earlier in the conversation.",
    "explores_alternatives": "You could surface a single decision recommendation sooner once the options have been reviewed.",
    "insufficient_evidence": "Add more meeting evidence by syncing additional meetings and reviewing transcript patterns.",
}


def _current_week_start() -> datetime:
    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday.replace(tzinfo=None)


def _serialize_insight(db: Session, insight: WeeklyInsight) -> dict:
    action = (
        db.query(MicroAction)
        .filter(MicroAction.insight_id == insight.id)
        .order_by(MicroAction.id.desc())
        .first()
    )
    return {
        "id": str(insight.id),
        "micro_action_id": str(action.id) if action else None,
        "strength": insight.strength,
        "growth_area": insight.growth_area,
        "evidence_summary": insight.evidence_summary,
        "micro_action": insight.micro_action,
        "status": "generated",
        "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
    }


def generate_meeting_insight(db: Session, meeting_id: int, user_id: int) -> dict:
    observations = (
        db.query(BehaviorObservation)
        .join(Meeting)
        .filter(BehaviorObservation.meeting_id == meeting_id, Meeting.user_id == user_id)
        .order_by(BehaviorObservation.created_at.desc())
        .all()
    )
    if not observations:
        return {
            "id": f"meeting-{meeting_id}-none",
            "meeting_id": str(meeting_id),
            "strength": "No analysis has been run for this meeting yet.",
            "growth_area": "Open the meeting and run Analyze meeting first.",
            "evidence_summary": "No behavior observations exist for this meeting.",
            "micro_action": "Analyze the meeting transcript, then come back for a coaching card.",
            "status": "insufficient_evidence",
        }

    counts = Counter(obs.behavior_label for obs in observations if obs.behavior_label != "insufficient_evidence")
    primary_label = counts.most_common(1)[0][0] if counts else "insufficient_evidence"
    status = "generated" if counts else "insufficient_evidence"
    return {
        "id": f"meeting-{meeting_id}",
        "meeting_id": str(meeting_id),
        "strength": LABEL_TO_STRENGTH.get(primary_label, "Your team sees patterns of thoughtful leadership."),
        "growth_area": LABEL_TO_GROWTH.get(primary_label, "You could continue building stronger leadership habits with more evidence."),
        "evidence_summary": "; ".join(obs.evidence_text for obs in observations[:3]),
        "micro_action": (
            "Before your next decision, ask one teammate for an alternative point of view."
            if primary_label in {"gives_direct_instructions", "explores_alternatives"}
            else "Before your next team conversation, invite one additional perspective and close with the decision you intend to make."
        ),
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_weekly_insight_for_user(db: Session, user_email: str = "demo@example.com") -> dict:
    user = db.query(User).filter_by(email=user_email).first()
    if user is None:
        return {
            "id": "no-user",
            "strength": "There is not enough evidence yet.",
            "growth_area": "Sync more meetings to generate a weekly insight.",
            "evidence_summary": "No user data is available yet.",
            "micro_action": "Connect your Granola account and sync a few recent meetings.",
            "status": "insufficient_evidence",
        }

    existing = (
        db.query(WeeklyInsight)
        .filter(
            WeeklyInsight.user_id == user.id,
            WeeklyInsight.generated_at >= _current_week_start(),
        )
        .order_by(WeeklyInsight.generated_at.desc())
        .first()
    )
    if existing is not None:
        return _serialize_insight(db, existing)

    observations = (
        db.query(BehaviorObservation)
        .join(Meeting)
        .filter(Meeting.user_id == user.id)
        .order_by(BehaviorObservation.created_at.desc())
        .all()
    )

    if not observations:
        return {
            "id": "no-observations",
            "strength": "There is not enough evidence yet.",
            "growth_area": "Add more meeting data to generate a weekly insight.",
            "evidence_summary": "No behavior observations have been created for this user.",
            "micro_action": "Sync a meeting and analyze its transcript.",
            "status": "insufficient_evidence",
        }

    counts = Counter(obs.behavior_label for obs in observations if obs.behavior_label != "insufficient_evidence")
    primary_label = counts.most_common(1)[0][0] if counts else "insufficient_evidence"

    strength = LABEL_TO_STRENGTH.get(primary_label, "Your team sees patterns of thoughtful leadership.")
    growth_area = LABEL_TO_GROWTH.get(primary_label, "You could continue building stronger leadership habits with more evidence.")
    evidence_summary = "; ".join(obs.evidence_text for obs in observations[:3])
    micro_action = (
        "Before your next decision, ask one teammate for an alternative point of view."
        if primary_label in {"gives_direct_instructions", "explores_alternatives"}
        else "Before your next team conversation, invite one additional perspective and close with the decision you intend to make."
    )

    insight = WeeklyInsight(
        user_id=user.id,
        meeting_id=observations[0].meeting_id,
        strength=strength,
        growth_area=growth_area,
        evidence_summary=evidence_summary,
        micro_action=micro_action,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)

    action = MicroAction(insight_id=insight.id, title=micro_action, status="planned")
    db.add(action)
    db.commit()
    db.refresh(action)

    return {
        "id": str(insight.id),
        "micro_action_id": str(action.id),
        "strength": strength,
        "growth_area": growth_area,
        "evidence_summary": evidence_summary,
        "micro_action": micro_action,
        "status": "generated",
        "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
    }
