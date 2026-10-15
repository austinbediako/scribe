from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import BehaviorObservation, Meeting, TranscriptSegment


PATTERN_GROUPS = {
    "asks_open_questions": [
        "what do you think",
        "what are your thoughts",
        "how do you see",
        "what else",
        "what would you recommend",
        "how would you approach",
        "any thoughts",
        "can you share",
    ],
    "gives_direct_instructions": [
        "i need you to",
        "please",
        "let's",
        "we should",
        "you need to",
        "we must",
        "make sure",
    ],
    "recognizes_contributions": [
        "thanks for",
        "thank you",
        "i appreciate",
        "great work",
        "nice job",
        "good job",
        "appreciate the progress",
    ],
    "invites_perspectives": [
        "what do you think",
        "how do you see",
        "any thoughts",
        "tell me more",
        "what are your thoughts",
    ],
    "explores_alternatives": [
        "what else",
        "other options",
        "before we decide",
        "alternative path",
        "different approach",
        "another way",
    ],
}


def _matches_any(text: str, patterns: list[str]) -> bool:
    lower_text = text.lower()
    return any(pattern in lower_text for pattern in patterns)


def analyze_meeting(db: Session, meeting_id: str | int) -> list[BehaviorObservation]:
    meeting = db.query(Meeting).filter(Meeting.id == int(meeting_id)).first()
    if not meeting:
        raise ValueError("Meeting not found")

    transcript_segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting.id)
        .order_by(TranscriptSegment.start_time_ms.asc().nullslast())
        .all()
    )

    observations: list[BehaviorObservation] = []
    seen: set[tuple[str, str]] = set()

    for segment in transcript_segments:
        text = (segment.text or "").strip()
        if not text:
            continue

        for behavior_label, patterns in PATTERN_GROUPS.items():
            if _matches_any(text, patterns):
                signature = (behavior_label, text)
                if signature in seen:
                    continue
                seen.add(signature)

                confidence = "high" if behavior_label in {"asks_open_questions", "explores_alternatives"} else "medium"
                observation = BehaviorObservation(
                    meeting_id=meeting.id,
                    behavior_label=behavior_label,
                    evidence_text=text,
                    confidence=confidence,
                    is_supported=True,
                )
                db.add(observation)
                observations.append(observation)

    if not observations:
        observation = BehaviorObservation(
            meeting_id=meeting.id,
            behavior_label="insufficient_evidence",
            evidence_text="No confident leadership behavior signals were found in the transcript.",
            confidence="low",
            is_supported=False,
        )
        db.add(observation)
        observations.append(observation)

    db.commit()
    return observations
