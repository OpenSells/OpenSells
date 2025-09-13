from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Tuple

import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.plans import get_limits
from backend.models import UserUsageMonthly

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")


def month_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m")

def _get_row(db: Session, user_id: int, period_key: str) -> UserUsageMonthly | None:
    return (
        db.query(UserUsageMonthly)
        .filter_by(user_id=user_id, period_yyyymm=period_key)
        .first()
    )


def _get_or_create(db: Session, user_id: int, period_key: str) -> UserUsageMonthly:
    row = _get_row(db, user_id, period_key)
    if not row:
        row = UserUsageMonthly(user_id=user_id, period_yyyymm=period_key)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def tareas_usadas_mes(db: Session, user_id: int) -> int:
    row = _get_row(db, user_id, month_key())
    return row.tasks if row else 0


def inc_tareas(db: Session, user_id: int, by: int = 1) -> int:
    row = _get_or_create(db, user_id, month_key())
    row.tasks += by
    db.commit()
    return row.tasks


def ia_mensajes_usados_mes(db: Session, user_id: int) -> int:
    row = _get_row(db, user_id, month_key())
    return row.ia_msgs if row else 0


def inc_ia_mensajes(db: Session, user_id: int, by: int = 1) -> int:
    row = _get_or_create(db, user_id, month_key())
    row.ia_msgs += by
    db.commit()
    return row.ia_msgs


def leads_extraidos_mes(db: Session, user_id: int) -> int:
    row = _get_row(db, user_id, month_key())
    return row.leads if row else 0


def inc_leads(db: Session, user_id: int, by: int) -> int:
    row = _get_or_create(db, user_id, month_key())
    row.leads += by
    db.commit()
    return row.leads


def csv_exports_mes(db: Session, user_id: int) -> int:
    row = _get_row(db, user_id, month_key())
    return row.csv_exports if row else 0


def inc_csv_exports(db: Session, user_id: int, by: int = 1) -> int:
    row = _get_or_create(db, user_id, month_key())
    row.csv_exports += by
    db.commit()
    return row.csv_exports


def free_searches_mes(db: Session, user_id: int) -> int:
    row = _get_row(db, user_id, month_key())
    return row.searches if row else 0


def inc_free_searches(db: Session, user_id: int, by: int = 1) -> int:
    row = _get_or_create(db, user_id, month_key())
    row.searches += by
    db.commit()
    return row.searches


# ------ IA usage helpers ---------------------------------------------------

def register_ia_message(db: Session, user) -> None:
    inc_ia_mensajes(db, user.id, 1)
    usage_log.info(f"[USAGE] mensajes_ia +1 user={user.id}")


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

def _error(feature: str, plan: str, limit: int | None, remaining: int | None, message: str, code: str = "LIMIT_EXCEEDED"):
    raise HTTPException(status_code=403, detail={"code": code, "message": message})


def can_use_ai(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int]:
    plan = get_limits(plan_name)
    used = ia_mensajes_usados_mes(db, user_id)
    remaining = plan.ia_mensajes - used
    return (remaining > 0, remaining)


def consume_ai(db: Session, user_id: int, plan_name: str):
    ok, remaining = can_use_ai(db, user_id, plan_name)
    if not ok:
        _error(
            "ai",
            plan_name,
            get_limits(plan_name).ia_mensajes,
            remaining,
            f"Has alcanzado el límite de mensajes de IA de tu plan para este mes (límite: {get_limits(plan_name).ia_mensajes}).",
            code="IA_QUOTA_REACHED",
        )
    inc_ia_mensajes(db, user_id, 1)


def can_export_csv(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None, int | None]:
    plan = get_limits(plan_name)
    if plan.csv_unlimited:
        return True, None, None
    used = csv_exports_mes(db, user_id)
    remaining = (plan.csv_exports_per_month or 0) - used
    return remaining > 0, remaining, plan.csv_rows_cap_free


def consume_csv_export(db: Session, user_id: int, plan_name: str):
    ok, remaining, _ = can_export_csv(db, user_id, plan_name)
    if not ok:
        _error(
            "csv",
            plan_name,
            get_limits(plan_name).csv_exports_per_month,
            remaining,
            "Límite de exportaciones alcanzado",
            code="CSV_QUOTA_REACHED",
        )
    inc_csv_exports(db, user_id, 1)


def can_start_search(db: Session, user_id: int, plan_name: str) -> Tuple[bool, int | None, int | None]:
    plan = get_limits(plan_name)
    if plan.type == "free":
        used = free_searches_mes(db, user_id)
        remaining = plan.searches_per_month - used
        return remaining > 0, remaining, plan.leads_cap_per_search
    else:
        used = leads_extraidos_mes(db, user_id)
        remaining = (plan.lead_credits_month or 0) - used
        return True, remaining, None


def consume_free_search(db: Session, user_id: int, plan_name: str):
    ok, remaining, _ = can_start_search(db, user_id, plan_name)
    if not ok:
        _error(
            "search",
            plan_name,
            get_limits(plan_name).searches_per_month,
            remaining,
            "Límite de búsquedas alcanzado",
            code="SEARCH_QUOTA_REACHED",
        )
    inc_free_searches(db, user_id, 1)


def consume_lead_credits(db: Session, user_id: int, plan_name: str, used: int):
    plan = get_limits(plan_name)
    if plan.lead_credits_month is not None:
        current = leads_extraidos_mes(db, user_id)
        if current + used > plan.lead_credits_month:
            _error(
                "leads",
                plan_name,
                plan.lead_credits_month,
                plan.lead_credits_month - current,
                "Límite de leads alcanzado",
                code="LEADS_QUOTA_REACHED",
            )
    inc_leads(db, user_id, used)
