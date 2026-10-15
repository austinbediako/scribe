from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import MicroAction, User, WeeklyInsight
from app.services.insight_service import generate_weekly_insight_for_user

router = APIRouter()


def _micro_action_id_for_insight(db: Session, insight_id: int) -> str | None:
    action = db.query(MicroAction).filter(MicroAction.insight_id == insight_id).order_by(MicroAction.id.desc()).first()
    return str(action.id) if action else None


@router.get("/api/insights/current")
def get_current_insight(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = generate_weekly_insight_for_user(db, user_email=user.email)
    return result


@router.get("/api/insights")
def list_insights(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    insights = (
        db.query(WeeklyInsight)
        .filter(WeeklyInsight.user_id == user.id)
        .order_by(WeeklyInsight.generated_at.desc())
        .all()
    )
    return [
        {
            "id": str(insight.id),
            "strength": insight.strength,
            "growth_area": insight.growth_area,
            "evidence_summary": insight.evidence_summary,
            "micro_action": insight.micro_action,
            "micro_action_id": _micro_action_id_for_insight(db, insight.id),
            "status": "generated",
            "generated_at": insight.generated_at,
        }
        for insight in insights
    ]


@router.get("/api/insights/{insight_id}")
def get_insight(
    insight_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    insight = (
        db.query(WeeklyInsight)
        .filter(WeeklyInsight.id == int(insight_id), WeeklyInsight.user_id == user.id)
        .first()
    )
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    return {
        "id": str(insight.id),
        "strength": insight.strength,
        "growth_area": insight.growth_area,
        "evidence_summary": insight.evidence_summary,
        "micro_action": insight.micro_action,
        "micro_action_id": _micro_action_id_for_insight(db, insight.id),
        "status": "generated",
        "generated_at": insight.generated_at,
    }