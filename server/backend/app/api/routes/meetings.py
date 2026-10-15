import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
)
from app.db.models import Meeting, MeetingCapture, TranscriptSegment
from app.services.recall_capture_service import RecallClient, RecallNotConfiguredError
from app.services.analysis_service import analyze_meeting

router = APIRouter()


def _scoped_meeting_query(db: Session, user, meeting_id: int | None = None):
    query = db.query(Meeting).filter(Meeting.user_id == user.id)
    if meeting_id is not None:
        query = query.filter(Meeting.id == meeting_id)
    return query, user


@router.get("/api/meetings")
def list_meetings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query, _ = _scoped_meeting_query(db, user)
    meetings = query.order_by(Meeting.created_at.desc()).all()
    results = []
    for meeting in meetings:
        has_transcript = db.query(TranscriptSegment.id).filter_by(meeting_id=meeting.id).first() is not None
        results.append(
            {
                "id": str(meeting.id),
                "granola_meeting_id": meeting.granola_meeting_id,
                "title": meeting.title,
                "source": "recall" if meeting.granola_meeting_id.startswith("recall:") else "granola",
                "started_at": meeting.started_at,
                "ended_at": meeting.ended_at,
                "created_at": meeting.created_at,
                "transcript_available": has_transcript,
            }
        )
    return results


@router.get("/api/meetings/{meeting_id}")
def get_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query, _ = _scoped_meeting_query(db, user, int(meeting_id))
    meeting = query.first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting.id)
        .order_by(TranscriptSegment.start_time_ms.asc().nullslast(), TranscriptSegment.id.asc())
        .all()
    )
    serialized = [
        {
            "id": str(segment.id),
            "speaker_name": segment.speaker_name,
            "speaker_id": segment.speaker_id,
            "text": segment.text,
            "start_time_ms": segment.start_time_ms,
            "end_time_ms": segment.end_time_ms,
        }
        for segment in segments
    ]
    return {
        "id": str(meeting.id),
        "granola_meeting_id": meeting.granola_meeting_id,
        "title": meeting.title,
        "source": "recall" if meeting.granola_meeting_id.startswith("recall:") else "granola",
        "started_at": meeting.started_at,
        "ended_at": meeting.ended_at,
        "created_at": meeting.created_at,
        "transcript_available": bool(serialized),
        "transcript": serialized,
    }


@router.post("/api/meetings/{meeting_id}/analyze")
def analyze_meeting_route(
    meeting_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query, _ = _scoped_meeting_query(db, user, int(meeting_id))
    meeting = query.first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        observations = analyze_meeting(db, meeting.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting.id)
        .all()
    )
    talk_time: dict[str, int] = {}
    for segment in segments:
        speaker = segment.speaker_name or "Unknown"
        start = segment.start_time_ms or 0
        end = segment.end_time_ms or 0
        duration = max(0, end - start)
        talk_time[speaker] = talk_time.get(speaker, 0) + duration

    return {
        "meeting_id": meeting_id,
        "status": "success",
        "observation_count": len(observations),
        "observations": [
            {
                "id": str(obs.id),
                "behavior_label": obs.behavior_label,
                "confidence": obs.confidence,
                "evidence_text": obs.evidence_text,
                "is_supported": obs.is_supported,
            }
            for obs in observations
        ],
        "metrics": {
            "talk_time_ms_by_speaker": talk_time,
        },
    }


@router.get("/api/meetings/{meeting_id}/transcript")
def get_meeting_transcript(
    meeting_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query, _ = _scoped_meeting_query(db, user, int(meeting_id))
    meeting = query.first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting.id)
        .order_by(TranscriptSegment.start_time_ms.asc().nullslast(), TranscriptSegment.id.asc())
        .all()
    )
    serialized = [
        {
            "id": str(segment.id),
            "speaker_name": segment.speaker_name,
            "speaker_id": segment.speaker_id,
            "text": segment.text,
            "start_time_ms": segment.start_time_ms,
            "end_time_ms": segment.end_time_ms,
        }
        for segment in segments
    ]
    return {
        "meeting_id": meeting_id,
        "segments": serialized,
        "transcript": "\n".join(
            f"{segment['speaker_name'] or 'Unknown'}: {segment['text']}" for segment in serialized
        ),
    }


@router.get("/api/meetings/{meeting_id}/video")
async def get_meeting_video(
    meeting_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query, _ = _scoped_meeting_query(db, user, int(meeting_id))
    meeting = query.first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.granola_meeting_id.startswith("recall:"):
        raise HTTPException(status_code=404, detail="Video is not available for this meeting.")

    bot_id = meeting.granola_meeting_id.split(":", 1)[1]
    capture = None
    if bot_id:
        capture = db.query(MeetingCapture).filter_by(recall_bot_id=bot_id).first()

    try:
        bot = await RecallClient().retrieve_bot(bot_id)
    except (httpx.HTTPError, ValueError, RecallNotConfiguredError):
        raise HTTPException(status_code=502, detail="Could not retrieve video from Recall.")

    recordings = bot.get("recordings")
    if not isinstance(recordings, list):
        raise HTTPException(status_code=404, detail="Video is not available for this meeting.")

    selected = None
    if capture is not None and capture.recall_recording_id:
        for recording in recordings:
            if isinstance(recording, dict) and recording.get("id") == capture.recall_recording_id:
                selected = recording
                break
    if selected is None:
        for recording in recordings:
            if not isinstance(recording, dict):
                continue
            status = recording.get("status")
            status_code = status.get("code") if isinstance(status, dict) else None
            if status_code in {None, "done"}:
                selected = recording
                break
    if selected is None:
        raise HTTPException(status_code=404, detail="Video is not available for this meeting.")

    media = selected.get("media_shortcuts")
    video = media.get("video_mixed") if isinstance(media, dict) else None
    video_data = video.get("data") if isinstance(video, dict) else None
    download_url = video_data.get("download_url") if isinstance(video_data, dict) else None
    if not isinstance(download_url, str):
        raise HTTPException(status_code=404, detail="Video is not available for this meeting.")

    participant_events = selected.get("media_shortcuts", {}).get("participant_events") if isinstance(selected.get("media_shortcuts"), dict) else None
    participant_events_data = participant_events.get("data") if isinstance(participant_events, dict) else None
    speaker_timeline_download_url = participant_events_data.get("speaker_timeline_download_url") if isinstance(participant_events_data, dict) else None

    return {
        "meeting_id": meeting_id,
        "recording_id": selected.get("id"),
        "download_url": download_url,
        "expires_at": selected.get("expires_at"),
        "format": video.get("format") if isinstance(video, dict) else "mp4",
        "status": (video.get("status", {}).get("code") if isinstance(video, dict) else None),
        "speaker_timeline_download_url": speaker_timeline_download_url,
    }

