from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class PlanConfig:
    """Configuration values for a subscription plan."""

    type: str  # "free" or "paid"
    # legacy limits kept for compatibility with existing endpoints
    searches_per_month: Optional[int] = None
    leads_cap_per_search: Optional[int] = None
    csv_exports_per_month: Optional[int] = None
    csv_rows_cap_free: Optional[int] = None

    # unified quota fields used by new enforcement code
    tareas_max: int = 0
    ia_mensajes: int = 0
    lead_credits_month: Optional[int] = None
    permite_notas: bool = False
    csv_exportacion: bool = False
    queue_priority: int = 0

    # ------------------------------------------------------------------
    # Backwards compatibility helpers
    # ------------------------------------------------------------------
    @property
    def tasks_active_max(self) -> int:  # pragma: no cover - simple delegation
        return self.tareas_max

    @property
    def ai_daily_limit(self) -> int:  # pragma: no cover - simple delegation
        return self.ia_mensajes

    @property
    def csv_unlimited(self) -> bool:  # pragma: no cover - simple delegation
        return self.csv_exportacion


PLANES: Dict[str, PlanConfig] = {
    "free": PlanConfig(
        type="free",
        searches_per_month=4,
        leads_cap_per_search=10,
        csv_exports_per_month=0,
        csv_rows_cap_free=10,
        tareas_max=4,
        ia_mensajes=5,
        permite_notas=False,
        csv_exportacion=False,
        queue_priority=0,
        lead_credits_month=40,
    ),
    "starter": PlanConfig(
        type="paid",
        lead_credits_month=150,
        tareas_max=20,
        ia_mensajes=20,
        permite_notas=True,
        csv_exportacion=True,
        queue_priority=1,
    ),
    "pro": PlanConfig(
        type="paid",
        lead_credits_month=600,
        tareas_max=100,
        ia_mensajes=100,
        permite_notas=True,
        csv_exportacion=True,
        queue_priority=2,
    ),
    "business": PlanConfig(
        type="paid",
        lead_credits_month=2000,
        tareas_max=500,
        ia_mensajes=500,
        permite_notas=True,
        csv_exportacion=True,
        queue_priority=3,
    ),
}


def get_plan_for_user(user) -> Tuple[str, PlanConfig]:
    name = (getattr(user, "plan", "free") or "free").strip().lower()
    return name, PLANES.get(name, PLANES["free"])


def get_limits(plan_name: str) -> PlanConfig:
    return PLANES.get(plan_name, PLANES["free"])

