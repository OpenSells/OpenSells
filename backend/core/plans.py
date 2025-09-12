from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class PlanConfig:
    type: str  # "free" or "paid"
    searches_per_month: Optional[int] = None
    leads_cap_per_search: Optional[int] = None
    csv_exports_per_month: Optional[int] = None
    csv_rows_cap_free: Optional[int] = None
    tasks_active_max: int = 0
    ai_daily_limit: int = 0
    queue_priority: int = 0
    # paid plans
    lead_credits_month: Optional[int] = None
    csv_unlimited: bool = False


PLANES: Dict[str, PlanConfig] = {
    "free": PlanConfig(
        type="free",
        searches_per_month=4,
        leads_cap_per_search=10,
        csv_exports_per_month=0,
        csv_rows_cap_free=10,
        tasks_active_max=4,
        ai_daily_limit=5,
        queue_priority=0,
    ),
    "starter": PlanConfig(
        type="paid",
        lead_credits_month=150,
        csv_unlimited=True,
        tasks_active_max=20,
        ai_daily_limit=20,
        queue_priority=1,
    ),
    "pro": PlanConfig(
        type="paid",
        lead_credits_month=600,
        csv_unlimited=True,
        tasks_active_max=100,
        ai_daily_limit=100,
        queue_priority=2,
    ),
    "business": PlanConfig(
        type="paid",
        lead_credits_month=2000,
        csv_unlimited=True,
        tasks_active_max=500,
        ai_daily_limit=500,
        queue_priority=3,
    ),
}


def get_plan_for_user(user) -> Tuple[str, PlanConfig]:
    name = (getattr(user, "plan", "free") or "free").strip().lower()
    return name, PLANES.get(name, PLANES["free"])


def get_limits(plan_name: str) -> PlanConfig:
    return PLANES.get(plan_name, PLANES["free"])

