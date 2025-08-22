from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session

from backend.models import Suscripcion, Usuario


def get_tenant_email(user: Usuario) -> str:
    """Return the canonical tenant key for the current user."""
    return user.email_lower


def get_tenant_filter(user: Usuario) -> Dict[str, str]:
    """Return a filter dict scoping queries to the current tenant."""
    return {"user_email_lower": get_tenant_email(user)}


def resolve_user_plan(user: Usuario, db: Session) -> str:
    """Resolve the user's plan prioritising active subscriptions."""
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
        return (user.plan or "pro").lower()
    return (user.plan or "free").lower()
