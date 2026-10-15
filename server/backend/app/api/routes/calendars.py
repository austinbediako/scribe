from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import CalendarConnection
from app.services.recall_capture_service import (
    connect_calendar_for_user,
    get_calendar_connection_events,
    list_calendar_connections,
    schedule_calendar_capture_for_user,
    serialize_calendar_connection,
    unschedule_calendar_capture_for_user,
)


router = APIRouter()


class CalendarConnectionRequest(BaseModel):
    platform: str = Field(pattern="^(google_calendar|microsoft_outlook)$")
    oauth_client_id: str = Field(min_length=1, max_length=2000)
    oauth_client_secret: str | None = Field(default=None, max_length=2000)
    oauth_refresh_token: str = Field(min_length=1, max_length=10000)
    oauth_email: str | None = None
    consent_confirmed: bool = True


class CalendarScheduleRequest(BaseModel):
    consent_confirmed: bool


@router.post("/api/integrations/recall/calendars", status_code=status.HTTP_201_CREATED)
async def create_calendar_connection(
    payload: CalendarConnectionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not payload.consent_confirmed:
        raise HTTPException(status_code=400, detail="Confirm consent and permission to connect this calendar.")
    try:
        connection = await connect_calendar_for_user(db, user, payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Recall could not create this calendar connection.") from exc
    return serialize_calendar_connection(connection)


@router.get("/api/integrations/recall/calendars")
def list_calendar_connections_route(
    db: Session = Depends(get_db), user=Depends(get_current_user)
):
    connections = list_calendar_connections(db, user)
    return [serialize_calendar_connection(connection) for connection in connections]


@router.get("/api/integrations/recall/calendars/{connection_id}/events")
async def list_calendar_connection_events(
    connection_id: int,
    updated_at_gte: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        events = await get_calendar_connection_events(db, user, connection_id, updated_at_gte)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Recall could not list calendar events.") from exc
    return {"events": events}


@router.post("/api/integrations/recall/calendars/{connection_id}/events/{event_id}/schedule")
async def schedule_calendar_event(
    connection_id: int,
    event_id: str,
    payload: CalendarScheduleRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not payload.consent_confirmed:
        raise HTTPException(status_code=400, detail="Confirm consent and permission to capture this meeting.")
    try:
        capture = await schedule_calendar_capture_for_user(
            db, user, connection_id, event_id, payload.consent_confirmed
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Recall could not schedule this calendar event.") from exc
    return {
        "id": str(capture.id),
        "calendar_event_id": capture.calendar_event_id,
        "calendar_connection_id": str(capture.calendar_connection_id) if capture.calendar_connection_id else None,
        "title": capture.title,
        "status": capture.status,
        "join_at": capture.join_at.isoformat(),
    }


@router.delete("/api/integrations/recall/calendars/{connection_id}", status_code=204)
async def delete_calendar_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    connection = (
        db.query(CalendarConnection)
        .filter(CalendarConnection.id == connection_id, CalendarConnection.user_id == user.id)
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Calendar connection not found.")
    db.delete(connection)
    db.commit()
    return None