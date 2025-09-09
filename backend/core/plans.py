from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user


class PlanLimits(BaseModel):
    leads_mensuales: Optional[int]
    ia_mensajes: Optional[int]
    tareas_max: Optional[int]
    csv_exportacion: bool
    permite_notas: bool


PLANS: Dict[str, PlanLimits] = {
    "free": PlanLimits(
        leads_mensuales=40,
        ia_mensajes=5,
        tareas_max=4,
        csv_exportacion=False,
        permite_notas=False,
    ),
    "basico": PlanLimits(
        leads_mensuales=200,
        ia_mensajes=50,
        tareas_max=None,
        csv_exportacion=True,
        permite_notas=True,
    ),
    "premium": PlanLimits(
        leads_mensuales=600,
        ia_mensajes=None,
        tareas_max=None,
        csv_exportacion=True,
        permite_notas=True,
    ),
}


TIER_ORDER = {"free": 0, "basico": 1, "premium": 2}


def get_plan_limits(plan: str) -> PlanLimits:
    return PLANS.get(plan, PLANS["free"])


def resolve_user_plan(usuario) -> tuple[str, PlanLimits]:
    plan_attr = getattr(usuario, "plan", "free") or "free"
    plan = str(plan_attr).strip().lower()
    limits = get_plan_limits(plan)
    return plan, limits


def validar_suscripcion(usuario=Depends(get_current_user)):
    if getattr(usuario, "suspendido", False):
        raise HTTPException(status_code=403, detail="Suscripción suspendida…")
    return usuario


def require_tier(min_tier: str):
    def dependency(usuario=Depends(validar_suscripcion)):
        plan, _ = resolve_user_plan(usuario)
        if TIER_ORDER.get(plan, 0) < TIER_ORDER.get(min_tier, 0):
            raise HTTPException(status_code=403, detail="plan_upgrade_required")
        return usuario

    return dependency


def require_feature(feature: str):
    def dependency(usuario=Depends(validar_suscripcion)):
        plan, limits = resolve_user_plan(usuario)
        if not getattr(limits, feature):
            raise HTTPException(status_code=403, detail=f"feature_not_available:{feature}")
        return usuario

    return dependency


__all__ = [
    "PlanLimits",
    "PLANS",
    "get_plan_limits",
    "resolve_user_plan",
    "validar_suscripcion",
    "require_tier",
    "require_feature",
]

