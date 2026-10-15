from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import MicroAction, User, WeeklyInsight

router = APIRouter()


class ActionUpdateRequest(BaseModel):
    status: str = "completed"


def _owned_actions_query(db: Session, user: User):
    return (
        db.query(MicroAction)
        .join(WeeklyInsight, MicroAction.insight_id == WeeklyInsight.id)
        .filter(WeeklyInsight.user_id == user.id)
    )


@router.get("/api/actions")
def list_actions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    actions = _owned_actions_query(db, user).order_by(MicroAction.created_at.desc()).all()
    return [
        {
            "id": str(action.id),
            "insight_id": str(action.insight_id) if action.insight_id is not None else None,
            "title": action.title,
            "status": action.status,
            "created_at": action.created_at,
            "updated_at": action.updated_at,
        }
        for action in actions
    ]


@router.patch("/api/actions/{action_id}")
def update_action(
    action_id: str,
    request: ActionUpdateRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        action_id_int = int(action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Action not found") from exc

    action = _owned_actions_query(db, user).filter(MicroAction.id == action_id_int).first()
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")

    new_status = request.status if request is not None else "completed"
    action.status = new_status
    db.commit()
    db.refresh(action)

    return {
        "id": str(action.id),
        "status": action.status,
        "message": "Micro-action status updated.",
    }