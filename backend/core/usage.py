from __future__ import annotations

from datetime import datetime
from typing import Tuple
from functools import wraps

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from psycopg2.errors import UndefinedTable
import logging

from backend.core.plan_config import get_limits
from backend.models import UsageCounter

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")


def month_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m")


def day_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m-%d")


def _get_row(db: Session, user_id: int, metric: str, period_key: str) -> UsageCounter | None:
    try:
        return (
            db.query(UsageCounter)
            .filter_by(user_id=user_id, metric=metric, period_key=period_key)
            .first()
        )
    except (ProgrammingError, UndefinedTable) as e:  # pragma: no cover - table missing
        if "usage_counters" in str(getattr(e, "orig", "")):
            logger.warning(
                "usage_counters table missing; returning 0 for %s/%s", metric, period_key
            )
            db.rollback()
            return None
        raise


def get_count(db: Session, user_id: int, metric: str, period_key: str) -> int:
    try:
        row = _get_row(db, user_id, metric, period_key)
        return row.count if row else 0
    except (ProgrammingError, UndefinedTable) as e:  # pragma: no cover - table missing
        if "usage_counters" in str(getattr(e, "orig", "")):
            logger.warning(
                "usage_counters table missing; returning 0 for %s/%s", metric, period_key
            )
            db.rollback()
            return 0
        raise


def inc_count(db: Session, user_id: int, metric: str, period_key: str, by: int = 1) -> int:
    try:
        row = _get_row(db, user_id, metric, period_key)
        if row:
            row.count += by
        else:
            row = UsageCounter(
                user_id=user_id, metric=metric, period_key=period_key, count=by
            )
            db.add(row)
        db.commit()
        return row.count
    except (ProgrammingError, UndefinedTable) as e:  # pragma: no cover - table missing
        if "usage_counters" in str(getattr(e, "orig", "")):
            logger.warning(
                "usage_counters table missing; cannot increment %s/%s", metric, period_key
            )
            db.rollback()
            return 0
        db.rollback()
        raise


# ------ IA usage helpers ---------------------------------------------------

def register_ia_message(db: Session, user) -> None:
    """Incrementa la métrica mensual de mensajes IA para el usuario."""
    inc_count(db, user.id, "mensajes_ia", month_key(), 1)
    usage_log.info(f"[USAGE] mensajes_ia +1 user={user.email_lower}")


def count_ia_when_called(db_getter, user_getter):
    """Decorador que registra mensajes_ia +1 cuando la función realmente invoca OpenAI."""
    def outer(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            kwargs.setdefault("_did_call_openai", False)
            res = await fn(*args, **kwargs)
            try:
                if kwargs.get("_did_call_openai"):
                    db = db_getter()
                    user = user_getter()
                    register_ia_message(db, user)
                else:
                    usage_log.info("[USAGE] skip_ia: no OpenAI call")
            except Exception as e:  # pragma: no cover - logging only
                usage_log.exception(f"[USAGE] register mensajes_ia failed: {e}")
            return res
        return wrapper

    return outer


# ------ limit helpers -----------------------------------------------------

def _error(feature: str, plan: str, limit: int | None, remaining: int | None, message: str):
    raise HTTPException(
        status_code=403,
        detail={
            "error": "limit_exceeded",
            "feature": feature,
            "plan": plan,
            "limit": limit,
            "remaining": remaining,
            "message": message,
        },
    )


def can_use_ai(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int]:
    plan = get_limits(plan_name)
    period = day_key()
    used = get_count(db, user_id, "ai_messages", period)
    remaining = plan.ai_daily_limit - used
    return (remaining > 0, remaining)


def consume_ai(db: Session, user_id: int, plan_name: str):
    ok, remaining = can_use_ai(db, user_id, plan_name)
    if not ok:
        _error("ai", plan_name, get_limits(plan_name).ai_daily_limit, remaining, "Límite diario de IA excedido")
    inc_count(db, user_id, "ai_messages", day_key(), 1)


def can_export_csv(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None, int | None]:
    plan = get_limits(plan_name)
    if plan.csv_unlimited:
        return True, None, None
    period = month_key()
    used = get_count(db, user_id, "csv_exports", period)
    remaining = (plan.csv_exports_per_month or 0) - used
    return remaining > 0, remaining, plan.csv_rows_cap_free


def consume_csv_export(db: Session, user_id: int, plan_name: str):
    ok, remaining, _ = can_export_csv(db, user_id, plan_name)
    if not ok:
        _error("csv", plan_name, get_limits(plan_name).csv_exports_per_month, remaining, "Límite de exportaciones alcanzado")
    inc_count(db, user_id, "csv_exports", month_key(), 1)


def can_start_search(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None, int | None]:
    plan = get_limits(plan_name)
    if plan.type == "free":
        period = month_key()
        used = get_count(db, user_id, "free_searches", period)
        remaining = plan.searches_per_month - used
        return remaining > 0, remaining, plan.leads_cap_per_search
    else:
        period = month_key()
        used = get_count(db, user_id, "lead_credits", period)
        remaining = (plan.lead_credits_month or 0) - used
        return True, remaining, None


def consume_free_search(db: Session, user_id: int, plan_name: str):
    ok, remaining, _ = can_start_search(db, user_id, plan_name)
    if not ok:
        _error("search", plan_name, get_limits(plan_name).searches_per_month, remaining, "Límite de búsquedas alcanzado")
    inc_count(db, user_id, "free_searches", month_key(), 1)


def consume_lead_credits(db: Session, user_id: int, plan_name: str, n: int):
    plan = get_limits(plan_name)
    period = month_key()
    used = get_count(db, user_id, "lead_credits", period)
    if plan.lead_credits_month is not None and used + n > plan.lead_credits_month:
        remaining = plan.lead_credits_month - used
        _error("lead_credits", plan_name, plan.lead_credits_month, remaining, "Créditos de lead insuficientes")
    inc_count(db, user_id, "lead_credits", period, n)


__all__ = [
    "month_key",
    "day_key",
    "get_count",
    "inc_count",
    "can_use_ai",
    "can_export_csv",
    "can_start_search",
    "consume_ai",
    "consume_csv_export",
    "consume_free_search",
    "consume_lead_credits",
    "register_ia_message",
    "count_ia_when_called",
]
