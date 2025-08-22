from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from backend.models import Suscripcion, Usuario

ACTIVE_STATES = {"active", "trialing"}


def resolve_user_plan(db: Session, user_email_lower: str) -> Dict:
    """Resolve plan info for the given tenant."""
    sub = (
        db.query(Suscripcion)
        .filter(Suscripcion.user_email_lower == user_email_lower)
        .order_by(Suscripcion.current_period_end.desc().nullslast())
        .first()
    )
    now = datetime.utcnow()
    if sub and sub.status in ACTIVE_STATES and (
        sub.current_period_end is None or sub.current_period_end >= now
    ):
        return {
            "plan_resuelto": "pro",
            "status": sub.status,
            "current_period_end": sub.current_period_end,
        }
    user_plan = (
        db.query(Usuario.plan)
        .filter(Usuario.email_lower == user_email_lower)
        .scalar()
    ) or "free"
    return {
        "plan_resuelto": "pro" if user_plan != "free" else "free",
        "status": "none",
        "current_period_end": None,
    }
