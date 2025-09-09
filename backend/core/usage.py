from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import os
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.plans import PLANES
from backend.models import Usuario

FEATURE_NEW_MODELS = os.getenv("FEATURE_NEW_MODELS", "false").lower() == "true"
if FEATURE_NEW_MODELS:
    from backend.models import UserUsageMonthly  # pragma: no cover

MSG_ESTANDAR = "Has alcanzado el límite de tu plan."


def get_period(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y%m")


def get_or_create_usage(db: Session, user_id: int, period: str):
    if not FEATURE_NEW_MODELS:
        return SimpleNamespace(leads=0, ia_msgs=0, tasks=0, csv_exports=0)
    UserUsageMonthly.__table__.create(bind=db.get_bind(), checkfirst=True)
    usage = (
        db.query(UserUsageMonthly)
        .filter_by(user_id=user_id, period_yyyymm=period)
        .first()
    )
    if usage is None:
        usage = UserUsageMonthly(
            user_id=user_id,
            period_yyyymm=period,
            leads=0,
            ia_msgs=0,
            tasks=0,
            csv_exports=0,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


_FEATURE_MAP = {
    "leads": ("leads", "leads_mensuales"),
    "ia_msgs": ("ia_msgs", "ia_mensajes"),
    "tasks": ("tasks", "tareas_max"),
    "csv_exports": ("csv_exports", "csv_exportacion"),
}


def check_and_inc(
    user: Usuario,
    feature: Literal["leads", "ia_msgs", "tasks", "csv_exports"],
    db: Session,
) -> None:
    if not FEATURE_NEW_MODELS:
        return
    period = get_period()
    usage = get_or_create_usage(db, user.id, period)
    campo_usage, campo_limit = _FEATURE_MAP[feature]

    limits = PLANES.get(user.plan, PLANES["free"])
    limit_value = getattr(limits, campo_limit)

    if feature == "csv_exports":
        if not limit_value:
            raise HTTPException(403, detail=MSG_ESTANDAR)
        limit_value = None  # Unlimited exports when allowed

    current = getattr(usage, campo_usage)
    if limit_value is not None and current + 1 > limit_value:
        raise HTTPException(403, detail=MSG_ESTANDAR)

    setattr(usage, campo_usage, current + 1)
    db.add(usage)
    db.commit()
    db.refresh(usage)
