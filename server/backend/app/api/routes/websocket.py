from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_user_by_token, resolve_request_user
from app.db.models import Meeting, TranscriptSegment
from app.db.session import SessionLocal
from app.services.granola_sync_service import sync_meetings_for_user

router = APIRouter()

_connections: defaultdict[int | None, Set[WebSocket]] = defaultdict(set)


async def _serialize_meetings(db: Session, user_id: int | None) -> list[dict[str, Any]]:
    query = db.query(Meeting)
    if user_id is not None:
        query = query.filter(Meeting.user_id == user_id)
    meetings = query.order_by(Meeting.created_at.desc()).all()
    results = []
    for meeting in meetings:
        has_transcript = (
            db.query(TranscriptSegment.id).filter_by(meeting_id=meeting.id).first() is not None
        )
        results.append(
            {
                "id": str(meeting.id),
                "granola_meeting_id": meeting.granola_meeting_id,
                "title": meeting.title,
                "source": "recall" if meeting.granola_meeting_id.startswith("recall:") else "granola",
                "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
                "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
                "transcript_available": has_transcript,
            }
        )
    return results


async def broadcast(user_id: int | None, data: dict[str, Any]) -> None:
    targets = list(_connections.get(user_id, set()))
    stale: list[WebSocket] = []
    for websocket in targets:
        try:
            await websocket.send_json(data)
        except Exception:
            stale.append(websocket)
    for websocket in stale:
        _connections[user_id].discard(websocket)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    token = websocket.query_params.get("token")
    db = SessionLocal()
    user = None
    try:
        user = get_user_by_token(db, token) if token else None
        resolved_user = resolve_request_user(db, user)
        _connections[resolved_user.id].add(websocket)

        await websocket.send_json(
            {
                "type": "connected",
                "user_email": resolved_user.email,
                "meetings": await _serialize_meetings(db, resolved_user.id),
            }
        )

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                message = {"type": raw}

            message_type = message.get("type") if isinstance(message, dict) else None

            if message_type == "sync":
                result = await sync_meetings_for_user(db, user_email=resolved_user.email)
                meetings = await _serialize_meetings(db, resolved_user.id)
                await broadcast(
                    resolved_user.id,
                    {
                        "type": "meetings.updated",
                        "meetings": meetings,
                        "synced_count": result.get("synced_count", 0),
                        "message": result.get("message", "Granola sync completed."),
                    },
                )
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        if resolved_user is not None:
            _connections[resolved_user.id].discard(websocket)
        db.close()