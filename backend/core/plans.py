from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import UsageCounter


class PlanLimits(BaseModel):
    leads_por_mes: Optional[int]
    mensajes_ia_por_mes: Optional[int]
    tareas_max: Optional[int]
    permite_notas: bool
    permite_export_csv: bool
    soporte: str


PLANS: Dict[str, PlanLimits] = {
    "free": PlanLimits(
        leads_por_mes=40,
        mensajes_ia_por_mes=5,
        tareas_max=4,
        permite_notas=False,
        permite_export_csv=False,
        soporte="email",
    ),
    "basico": PlanLimits(
        leads_por_mes=200,
        mensajes_ia_por_mes=50,
        tareas_max=None,
        permite_notas=True,
        permite_export_csv=True,
        soporte="email_prioritario",
    ),
    "premium": PlanLimits(
        leads_por_mes=600,
        mensajes_ia_por_mes=None,
        tareas_max=None,
        permite_notas=True,
        permite_export_csv=True,
        soporte="whatsapp",
    ),
}


TIER_ORDER = {"free": 0, "basico": 1, "premium": 2}


def get_plan_limits(plan: str) -> PlanLimits:
    """Return limits for plan, defaulting to free."""
    return PLANS.get(plan, PLANS["free"])


def resolve_user_plan(usuario) -> tuple[str, PlanLimits]:
    plan = (usuario.plan or "free").strip().lower()
    limits = get_plan_limits(plan)
    return plan, limits


def require_tier(min_tier: str):
    def dependency(usuario=Depends(get_current_user)):
        plan, _ = resolve_user_plan(usuario)
        if TIER_ORDER.get(plan, 0) < TIER_ORDER.get(min_tier, 0):
            raise HTTPException(status_code=403, detail="plan_upgrade_required")
        return usuario

    return dependency


def require_feature(feature: str):
    def dependency(usuario=Depends(get_current_user)):
        plan, limits = resolve_user_plan(usuario)
        if not getattr(limits, feature):
            raise HTTPException(status_code=403, detail=f"feature_not_available:{feature}")
        return usuario

    return dependency


def enforce_quota(metric: str, period: str = "month"):
    def dependency(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
        plan, limits = resolve_user_plan(usuario)
        limit_value = getattr(limits, metric)
        # Skip quota enforcement if no user id or limit is unlimited
        if limit_value is None or getattr(usuario, "id", None) is None:
            return usuario
        # Ensure table exists
        UsageCounter.__table__.create(bind=db.get_bind(), checkfirst=True)

        now = datetime.utcnow()
        period_key = now.strftime("%Y-%m") if period == "month" else now.strftime("%Y-%m-%d")
        counter = (
            db.query(UsageCounter)
            .filter_by(user_id=usuario.id, metric=metric, period_key=period_key)
            .first()
        )
        if counter and counter.count >= limit_value:
            raise HTTPException(status_code=403, detail=f"quota_exceeded:{metric}")
        if counter:
            counter.count += 1
        else:
            counter = UsageCounter(
                user_id=usuario.id, metric=metric, period_key=period_key, count=1
            )
            db.add(counter)
        db.commit()
        return usuario

    return dependency


__all__ = [
    "PlanLimits",
    "PLANS",
    "get_plan_limits",
    "resolve_user_plan",
    "require_tier",
    "require_feature",
    "enforce_quota",
]
