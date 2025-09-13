from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.plan_config import PLANES, get_limits as _get_plan_limits
from backend.core.stripe_mapping import stripe_price_to_plan
from backend.core.usage import (
    day_key,
    month_key,
    get_count,
)
from backend.models import LeadTarea

logger = logging.getLogger(__name__)


class PlanService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    def get_effective_plan(self, user) -> Tuple[str, object]:
        """Resolve the effective plan for a user.

        DB plan has priority. If not present, try Stripe price mapping.
        Fallback to "free" and log a warning.
        """
        db_plan = (getattr(user, "plan", "") or "free").strip().lower()
        price_id = getattr(user, "stripe_price_id", None)
        plan_name = db_plan if db_plan in PLANES else None
        if not plan_name and price_id:
            mapped = stripe_price_to_plan(price_id)
            if mapped in PLANES:
                plan_name = mapped
        if not plan_name:
            logger.warning(
                "Unknown plan for user %s: db_plan=%s price_id=%s; defaulting to free",
                getattr(user, "email", getattr(user, "id", "?")),
                db_plan,
                price_id,
            )
            plan_name = "free"
        logger.info(
            "plan_resolved email=%s db_plan=%s stripe_price_id=%s effective_plan=%s",
            getattr(user, "email", getattr(user, "id", "?")),
            db_plan,
            price_id,
            plan_name,
        )
        return plan_name, PLANES[plan_name]

    # ------------------------------------------------------------------
    def get_limits(self, plan_name: str) -> dict:
        plan = _get_plan_limits(plan_name)
        return asdict(plan)

    # ------------------------------------------------------------------
    def get_quotas(self, user) -> dict:
        plan_name, plan = self.get_effective_plan(user)
        mkey = month_key()
        dkey = day_key()

        degraded = False
        try:
            self.db.execute(text("SELECT 1 FROM usage_counters LIMIT 1"))
            lead_used = get_count(self.db, user.id, "lead_credits", mkey)
            free_used = get_count(self.db, user.id, "free_searches", mkey)
            csv_used = get_count(self.db, user.id, "csv_exports", mkey)
            ai_used = get_count(self.db, user.id, "ai_messages", dkey)
            ia_month_used = get_count(self.db, user.id, "mensajes_ia", mkey)
        except Exception as e:  # pragma: no cover - table missing
            logger.warning("usage_counters table missing or inaccessible: %s", e)
            self.db.rollback()
            degraded = True
            lead_used = free_used = csv_used = ai_used = ia_month_used = 0

        tasks_current = (
            self.db.query(LeadTarea)
            .filter(
                LeadTarea.user_email_lower == user.email_lower,
                LeadTarea.completado == False,
            )
            .count()
        )

        limits = {
            "searches_per_month": plan.searches_per_month if plan.type == "free" else None,
            "leads_cap_per_search": plan.leads_cap_per_search if plan.type == "free" else None,
            "csv_exports_per_month": plan.csv_exports_per_month if plan.type == "free" else None,
            "csv_rows_cap_free": plan.csv_rows_cap_free if plan.type == "free" else None,
            "lead_credits_month": plan.lead_credits_month if plan.type == "paid" else None,
            "tasks_active_max": plan.tasks_active_max,
            "ai_daily_limit": plan.ai_daily_limit,
        }

        usage = {
            "lead_credits": {
                "used": lead_used,
                "remaining": (plan.lead_credits_month - lead_used)
                if plan.lead_credits_month is not None
                else None,
                "period": mkey,
            },
            "free_searches": {
                "used": free_used,
                "remaining": (plan.searches_per_month - free_used)
                if plan.searches_per_month is not None
                else None,
                "period": mkey,
            },
            "csv_exports": {
                "used": csv_used,
                "remaining": (plan.csv_exports_per_month - csv_used)
                if plan.csv_exports_per_month is not None
                else None,
                "period": mkey,
            },
            "ai_messages": {
                "used_today": ai_used,
                "remaining_today": plan.ai_daily_limit - ai_used,
                "period": dkey,
            },
            "mensajes_ia": {"used": ia_month_used, "period": mkey},
            "tasks_active": {"current": tasks_current, "limit": plan.tasks_active_max},
        }

        remaining = {
            "lead_credits": usage["lead_credits"]["remaining"],
            "free_searches": usage["free_searches"]["remaining"],
            "csv_exports": usage["csv_exports"]["remaining"],
            "ai_messages": usage["ai_messages"]["remaining_today"],
            "tasks_active": plan.tasks_active_max - tasks_current,
            "mensajes_ia": None,
        }

        result = {
            "plan": plan_name,
            "limits": limits,
            "usage": usage,
            "remaining": remaining,
        }
        if degraded:
            result["meta"] = {"degraded": True, "reason": "usage_counters_missing"}
        return result

    # ------------------------------------------------------------------
    def get_usage(self, user) -> dict:
        return self.get_quotas(user)["usage"]

