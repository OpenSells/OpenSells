from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple
import logging

from sqlalchemy.orm import Session

from backend.core.plan_config import get_limits
from backend.core.usage_service import UsageService

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")

# Period helpers --------------------------------------------------------------

def month_key(dt: datetime | None = None) -> str:
    return UsageService.get_period_yyyymm(dt)


def day_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d")

# Basic counter helpers -------------------------------------------------------

_metric_map = {
    "ai_messages": "ia_msgs",
    "csv_exports": "csv_exports",
    "free_searches": "free_searches",
    "lead_credits": "lead_credits",
    "tasks": "tasks",
}


def _resolve_metric(metric: str, plan_type: str | None = None) -> str | None:
    if metric == "leads":
        return "free_searches" if plan_type == "free" else "lead_credits"
    return _metric_map.get(metric)


def get_count(
    db: Session, user_id: int, metric: str, period_key: str, plan_type: str | None = None
) -> int:
    svc = UsageService(db)
    period = period_key[:6]
    kind = _resolve_metric(metric, plan_type)
    if not kind:
        return 0
    return svc.get_usage(user_id, period).get(kind, 0)


def inc_count(
    db: Session,
    user_id: int,
    metric: str,
    period_key: str,
    by: int = 1,
    plan_type: str | None = None,
) -> int:
    svc = UsageService(db)
    kind = _resolve_metric(metric, plan_type)
    if not kind:
        return 0
    svc.increment(user_id, kind, by)
    return svc.get_usage(user_id, period_key[:6]).get(kind, 0)


def register_ia_message(db: Session, user) -> None:
    usage_log.info(f"[USAGE] mensajes_ia +1 user={user.email_lower}")

# Feature helpers -------------------------------------------------------------

def can_use_ai(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None]:
    plan = get_limits(plan_name)
    period = month_key()
    used = get_count(db, user_id, "ai_messages", period)
    limit = plan.ai_daily_limit
    remaining = None if limit is None else limit - used
    return (remaining is None or remaining > 0, remaining)


def consume_csv_export(db: Session, user_id: int, plan_name: str):
    inc_count(db, user_id, "csv_exports", month_key(), 1)


def can_export_csv(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None, int | None]:
    plan = get_limits(plan_name)
    if plan.csv_unlimited:
        return True, None, None
    period = month_key()
    used = get_count(db, user_id, "csv_exports", period)
    remaining = (plan.csv_exports_per_month or 0) - used
    return remaining > 0, remaining, plan.csv_rows_cap_free


def can_start_search(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None, int | None]:
    plan = get_limits(plan_name)
    period = month_key()
    if plan.type == "free":
        used = get_count(db, user_id, "free_searches", period)
        remaining = plan.searches_per_month - used
        return remaining > 0, remaining, plan.leads_cap_per_search
    else:
        used = get_count(db, user_id, "lead_credits", period)
        remaining = (plan.lead_credits_month or 0) - used
        return True, remaining, None


def consume_free_search(db: Session, user_id: int, plan_name: str):
    inc_count(db, user_id, "free_searches", month_key(), 1)


def consume_lead_credits(db: Session, user_id: int, plan_name: str, n: int):
    inc_count(db, user_id, "lead_credits", month_key(), n)


__all__ = [
    "month_key",
    "day_key",
    "get_count",
    "inc_count",
    "can_use_ai",
    "register_ia_message",
    "can_export_csv",
    "consume_csv_export",
    "can_start_search",
    "consume_free_search",
    "consume_lead_credits",
]
