from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session

from backend.models import Suscripcion, Usuario


def get_tenant_filter(user: Usuario) -> Dict[str, str]:
    """Return a consistent tenant filter for queries."""
    return {"user_email_lower": user.email_lower}


def resolve_user_plan(user: Usuario, db: Session) -> str:
    """Resolve a user's plan considering active subscriptions."""
    if user.plan and user.plan.lower() != "free":
        now = datetime.utcnow()
        sus = (
            db.query(Suscripcion)
            .filter_by(user_email_lower=user.email_lower)
            .filter(
                Suscripcion.status.in_(["active", "trialing"]),
                Suscripcion.current_period_end >= now,
            )
            .first()
        )
        if sus:
            return user.plan
    return "free"
