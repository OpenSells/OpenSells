from __future__ import annotations

import os
from typing import Optional

from backend.core.plan_config import PLANES

# Mapping de price_id de Stripe a nuestros nombres de planes
PRICE_TO_PLAN = {
    os.getenv("STRIPE_PRICE_FREE"): "free",
    os.getenv("STRIPE_PRICE_STARTER"): "starter",
    os.getenv("STRIPE_PRICE_PRO"): "pro",
    os.getenv("STRIPE_PRICE_BUSINESS"): "business",
}

# Limpiamos claves None
PRICE_TO_PLAN = {k: v for k, v in PRICE_TO_PLAN.items() if k}


def resolve_user_plan(user) -> str:
    """Resuelve el plan de un usuario utilizando Stripe si hay price_id.

    Si no se encuentra mapeo o no hay price_id, cae al atributo ``plan`` del
    usuario y finalmente a ``free``.
    """

    price_id: Optional[str] = getattr(user, "stripe_price_id", None)
    if price_id and price_id in PRICE_TO_PLAN:
        plan = PRICE_TO_PLAN[price_id]
    else:
        plan = getattr(user, "plan", "free") or "free"

    plan = str(plan).strip().lower()
    if plan not in PLANES:
        return "free"
    return plan


__all__ = ["PRICE_TO_PLAN", "resolve_user_plan"]
