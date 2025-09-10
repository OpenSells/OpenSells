from __future__ import annotations

from datetime import datetime
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.plan_config import get_limits
from backend.models import UsageCounter, LeadTarea


# Helpers de periodo

def month_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m")


def day_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m-%d")


# Acceso a los contadores

def _get_counter(db: Session, user_id: int, metric: str, period_key: str) -> UsageCounter:
    row = (
        db.query(UsageCounter)
        .filter_by(user_id=user_id, metric=metric, period_key=period_key)
        .first()
    )
    if not row:
        row = UsageCounter(user_id=user_id, metric=metric, period_key=period_key, count=0)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_count(db: Session, user_id: int, metric: str, period_key: str) -> int:
    row = (
        db.query(UsageCounter)
        .filter_by(user_id=user_id, metric=metric, period_key=period_key)
        .first()
    )
    return row.count if row else 0


def inc_count(db: Session, user_id: int, metric: str, period_key: str, by: int = 1) -> None:
    row = _get_counter(db, user_id, metric, period_key)
    row.count += by
    db.add(row)
    db.commit()


# Funciones de comprobación

def can_use_ai(db: Session, user_id: int, plan: str) -> Tuple[bool, int]:
    limits = get_limits(plan)
    key = day_key()
    used = get_count(db, user_id, "ai_messages", key)
    remaining = limits.ai_daily_limit - used
    return used < limits.ai_daily_limit, max(0, remaining)


def can_export_csv(db: Session, user_id: int, plan: str) -> Tuple[bool, int | None, int | None]:
    limits = get_limits(plan)
    if limits.csv_unlimited:
        return True, None, None
    key = month_key()
    used = get_count(db, user_id, "csv_exports", key)
    remaining = limits.csv_exports_per_month - used
    return used < limits.csv_exports_per_month, max(0, remaining), limits.csv_rows_cap_free


def can_start_search(db: Session, user_id: int, plan: str) -> Tuple[bool, int | None, int | None]:
    limits = get_limits(plan)
    key = month_key()
    if limits.type == "free":
        used = get_count(db, user_id, "free_searches", key)
        remaining = limits.searches_per_month - used
        return used < limits.searches_per_month, max(0, remaining), limits.leads_cap_per_search
    else:
        used = get_count(db, user_id, "lead_credits", key)
        remaining = limits.lead_credits_month - used
        return True, max(0, remaining), None


# Consumo

def consume_ai(db: Session, user_id: int, by: int = 1) -> None:
    inc_count(db, user_id, "ai_messages", day_key(), by)


def consume_csv_export(db: Session, user_id: int, by: int = 1) -> None:
    inc_count(db, user_id, "csv_exports", month_key(), by)


def consume_free_search(db: Session, user_id: int, by: int = 1) -> None:
    inc_count(db, user_id, "free_searches", month_key(), by)


def consume_lead_credits(db: Session, user_id: int, n: int) -> None:
    inc_count(db, user_id, "lead_credits", month_key(), n)


# Helpers varios

def count_active_tasks(db: Session, email_lower: str) -> int:
    return (
        db.query(LeadTarea)
        .filter(LeadTarea.user_email_lower == email_lower, LeadTarea.completado == False)
        .count()
    )


def limit_error(feature: str, plan: str, limit: int, remaining: int, message: str):
    payload = {
        "error": "limit_exceeded",
        "feature": feature,
        "plan": plan,
        "limit": limit,
        "remaining": remaining,
        "message": message,
    }
    raise HTTPException(status_code=403, detail=payload)


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
    "limit_error",
]
