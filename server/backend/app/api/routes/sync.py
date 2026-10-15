from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, get_db, resolve_request_user
from app.services.granola_sync_service import sync_meetings_for_user

router = APIRouter()


@router.post("/api/integrations/granola/sync")
async def sync_granola_meetings(
    db: Session = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    resolved_user = resolve_request_user(db, user)
    return await sync_meetings_for_user(db, user_email=resolved_user.email)