from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.plans import resolve_user_plan, get_plan_limits
from backend.models import UserUsageMonthly


MSG_ESTANDAR = "Límite del plan superado"


def get_period(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y%m")


def get_or_create_usage(db: Session, user_id: int, period: str) -> UserUsageMonthly:
    UserUsageMonthly.__table__.create(bind=db.get_bind(), checkfirst=True)
    usage = (
        db.query(UserUsageMonthly)
        .filter_by(user_id=user_id, period_yyyymm=period)
        .first()
    )
    if not usage:
        usage = UserUsageMonthly(user_id=user_id, period_yyyymm=period)
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def check_and_inc(
    db: Session,
    usuario,
    feature: Literal["leads", "ia_msgs", "tasks", "csv_exports"],
    amount: int = 1,
):
    if getattr(usuario, "id", None) is None:
        return
    plan, limits = resolve_user_plan(usuario)
    period = get_period()
    usage = get_or_create_usage(db, usuario.id, period)

    if feature == "leads":
        limit = limits.leads_mensuales
        current = usage.leads
        if limit is not None and current + amount > limit:
            raise HTTPException(status_code=403, detail=MSG_ESTANDAR)
        usage.leads = current + amount
    elif feature == "ia_msgs":
        limit = limits.ia_mensajes
        current = usage.ia_msgs
        if limit is not None and current + amount > limit:
            raise HTTPException(status_code=403, detail=MSG_ESTANDAR)
        usage.ia_msgs = current + amount
    elif feature == "tasks":
        limit = limits.tareas_max
        current = usage.tasks
        if limit is not None and current + amount > limit:
            raise HTTPException(status_code=403, detail=MSG_ESTANDAR)
        usage.tasks = current + amount
    elif feature == "csv_exports":
        if not limits.csv_exportacion:
            raise HTTPException(status_code=403, detail=MSG_ESTANDAR)
        usage.csv_exports = usage.csv_exports + amount
    else:
        raise ValueError("feature desconocida")

    db.add(usage)
    db.commit()


__all__ = [
    "get_period",
    "get_or_create_usage",
    "check_and_inc",
    "MSG_ESTANDAR",
]

