from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Tuple

from sqlalchemy.orm import Session

from backend.core.plan_service import get_limits
from backend.core.usage_service import UsageService, UsageDailyService

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")

AI_KEY = "mensajes_ia"
AI_ALIASES_READ = ("mensajes_ia", "ai_messages", "ia_mensajes", "ia_msgs")
UNLIMITED_TOKENS = {
    None,
    True,
    "∞",
    "unlimited",
    "ilimitado",
    "sin limite",
    "sin límite",
    "infinite",
    "infinito",
    "true",
    "ilimitada",
}

# Period helpers --------------------------------------------------------------

def month_key(dt: datetime | None = None) -> str:
    return UsageService.get_period_yyyymm(dt)


def day_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d")

# Basic counter helpers -------------------------------------------------------

_metric_map = {
    AI_KEY: ("ia_msgs", "daily"),
    "csv_exports": ("csv_exports", "monthly"),
    "exportaciones": ("csv_exports", "monthly"),
    "free_searches": ("leads", "monthly"),
    "busquedas": ("leads", "monthly"),
    "lead_credits": ("leads", "monthly"),
    "lead_credits_month": ("leads", "monthly"),
}


_metric_aliases = {
    "ai_messages": AI_KEY,
    "ia_mensajes": AI_KEY,
    "ia_msgs": AI_KEY,
}


def _resolve_metric(metric: str):
    canonical = _metric_aliases.get(metric, metric)
    return canonical, _metric_map.get(canonical)


def get_count(db: Session, user_id: int, metric: str, period_key: str) -> int:
    canonical, mapping = _resolve_metric(metric)
    if not mapping:
        return 0
    kind, period_type = mapping
    if period_type == "daily":
        svc = UsageDailyService(db)
        period = period_key if len(period_key) == 8 else svc.get_period_yyyymmdd()
        usage = svc.get_usage(user_id, period)
        if canonical == AI_KEY:
            total = 0
            seen: set[str] = set()
            for key in AI_ALIASES_READ:
                if key in usage and key not in seen:
                    try:
                        total += int(usage.get(key) or 0)
                    except (TypeError, ValueError):
                        continue
                    seen.add(key)
            return total
        return int(usage.get(kind, 0))
    svc = UsageService(db)
    period = period_key[:6]
    usage = svc.get_usage(user_id, period)
    value = usage.get(kind, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def inc_count(db: Session, user_id: int, metric: str, period_key: str, by: int = 1) -> int:
    canonical, mapping = _resolve_metric(metric)
    if not mapping:
        return 0
    kind, period_type = mapping
    if period_type == "daily":
        svc = UsageDailyService(db)
        period = period_key if len(period_key) == 8 else svc.get_period_yyyymmdd()
        svc.increment(user_id, kind, by, period)
        return svc.get_usage(user_id, period).get(kind, 0)
    svc = UsageService(db)
    svc.increment(user_id, kind, by, period_key[:6])
    usage = svc.get_usage(user_id, period_key[:6])
    value = usage.get(kind, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def register_ia_message(db: Session, user) -> None:
    usage_log.info(f"[USAGE] mensajes_ia +1 user={user.email_lower}")
    inc_count(db, user.id, AI_KEY, day_key(), 1)

# Feature helpers -------------------------------------------------------------

def _ai_used_today(db: Session, user_id: int) -> int:
    today = day_key()
    used = 0
    for key in AI_ALIASES_READ:
        try:
            used = max(used, int(get_count(db, user_id, key, today)))
        except Exception:  # noqa: BLE001 - defensive against legacy data types
            continue
    return used


def _normalize_ai_limit_value(raw_limit) -> int | None:
    """Return an integer limit or None if unlimited."""

    if raw_limit in UNLIMITED_TOKENS:
        return None
    if isinstance(raw_limit, bool):
        return None if raw_limit else 0
    if isinstance(raw_limit, (int, float)):
        return int(raw_limit)
    if isinstance(raw_limit, dict):
        for key in ("limit", "max", "value", "quota", "allowed"):
            if key in raw_limit:
                return _normalize_ai_limit_value(raw_limit[key])
        return 0
    if isinstance(raw_limit, str):
        normalized = raw_limit.strip().lower()
        if not normalized:
            return 0
        if normalized in UNLIMITED_TOKENS:
            return None
        normalized = normalized.replace(",", "")
        try:
            return int(float(normalized))
        except (TypeError, ValueError):
            return 0
    return 0


def get_ai_quota_state(
    db: Session, user_id: int, plan_name: str
) -> dict[str, int | None | bool]:
    """Return a dict with limit, used, remaining and ok flag for AI usage."""

    from backend.core.plan_service import PlanService

    svc = PlanService(db)
    limits = svc.get_limits(plan_name) or {}
    limit_value = _normalize_ai_limit_value(limits.get("ai_daily_limit"))

    used = _ai_used_today(db, user_id)

    if limit_value is None:
        remaining = None
        ok = True
    else:
        remaining = max(limit_value - used, 0)
        ok = remaining > 0

    usage_log.info(
        "AI quota check user=%s plan=%s limit=%s used=%s remaining=%s",
        user_id,
        plan_name,
        limit_value,
        used,
        remaining,
    )

    return {"ok": ok, "limit": limit_value, "used": used, "remaining": remaining}


def can_use_ai(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None]:
    """Return whether the user can consume an AI message and remaining quota."""

    state = get_ai_quota_state(db, user_id, plan_name)
    return state["ok"], state["remaining"]


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
        remaining = (plan.searches_per_month or 0) - used
        return remaining > 0, max(remaining, 0), plan.leads_cap_per_search
    else:
        used = get_count(db, user_id, "lead_credits", period)
        if plan.lead_credits_month is None:
            return True, None, None
        remaining = plan.lead_credits_month - used
        return remaining > 0, max(remaining, 0), None


def consume_free_search(db: Session, user_id: int, plan_name: str):
    inc_count(db, user_id, "free_searches", month_key(), 1)


def consume_lead_credits(db: Session, user_id: int, plan_name: str, n: int):
    inc_count(db, user_id, "lead_credits", month_key(), n)


__all__ = [
    "month_key",
    "day_key",
    "get_count",
    "inc_count",
    "get_ai_quota_state",
    "can_use_ai",
    "register_ia_message",
    "can_export_csv",
    "consume_csv_export",
    "can_start_search",
    "consume_free_search",
    "consume_lead_credits",
]
