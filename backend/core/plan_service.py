from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Tuple

from sqlalchemy.orm import Session

from backend.core.plan_config import PLANES, get_limits as _get_plan_limits
from backend.core.stripe_mapping import stripe_price_to_plan
from backend.core.usage_service import UsageService
from backend.models import LeadTarea

logger = logging.getLogger(__name__)


def get_limits(plan_name: str):
    """Return the dataclass with plan limits for the given plan name."""
    normalized = (plan_name or "free").strip().lower()
    return _get_plan_limits(normalized)


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
        plan = get_limits(plan_name)
        return asdict(plan)

    # ------------------------------------------------------------------
    def get_quotas(self, user) -> dict:
        plan_name, plan = self.get_effective_plan(user)
        usage_svc = UsageService(self.db)
        period = usage_svc.get_period_yyyymm()
        counts = usage_svc.get_usage(user.id, period) or {}

        from backend.core.usage_helpers import AI_ALIASES_READ, day_key, get_count

        today = day_key()
        ia_used_today = 0
        for key in AI_ALIASES_READ:
            try:
                ia_used_today = max(
                    ia_used_today, int(get_count(self.db, user.id, key, today))
                )
            except Exception as exc:  # noqa: BLE001 - legacy rows may not cast cleanly
                logger.debug(
                    "failed to read ai usage alias=%s user_id=%s: %s",
                    key,
                    getattr(user, "id", None),
                    exc,
                )
                continue

        ai_daily_limit = plan.ai_daily_limit
        ai_remaining_today = (
            None if ai_daily_limit is None else max(int(ai_daily_limit) - ia_used_today, 0)
        )
        day_period = today

        leads_used = int(counts.get("leads", 0) or 0)
        tasks_used = int(counts.get("tasks", 0) or 0)
        csv_exports_used = int(counts.get("csv_exports", 0) or 0)

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
            "ai_daily_limit": ai_daily_limit,
        }
        limits["mensajes_ia"] = ai_daily_limit
        limits["ai_messages"] = ai_daily_limit
        limits["ia_mensajes"] = ai_daily_limit
        limits["ia_msgs"] = ai_daily_limit

        usage = {
            "leads": {
                "used": leads_used,
                "remaining": (plan.lead_credits_month - leads_used)
                if plan.lead_credits_month is not None
                else None,
                "period": period,
            },
            "ia_msgs": {
                "used": ia_used_today,
                "period": day_period,
                "used_today": ia_used_today,
                "remaining_today": ai_remaining_today,
                "limit": ai_daily_limit,
            },
            "ai_messages": {
                "used": ia_used_today,
                "used_today": ia_used_today,
                "remaining_today": ai_remaining_today,
                "limit": ai_daily_limit,
                "period": day_period,
            },
            "tasks": {"used": tasks_used, "period": period},
            "csv_exports": {
                "used": csv_exports_used,
                "remaining": (plan.csv_exports_per_month - csv_exports_used)
                if plan.csv_exports_per_month is not None
                else None,
                "period": period,
            },
            "tasks_active": {"current": tasks_current, "limit": plan.tasks_active_max},
        }

        if plan.type == "free":
            usage["searches"] = {
                "used": leads_used,
                "remaining": (plan.searches_per_month - leads_used)
                if plan.searches_per_month is not None
                else None,
                "period": period,
            }
        else:
            usage["lead_credits"] = {
                "used": leads_used,
                "remaining": (plan.lead_credits_month - leads_used)
                if plan.lead_credits_month is not None
                else None,
                "period": period,
            }

        usage.setdefault("leads_mes", leads_used)
        usage["mensajes_ia"] = ia_used_today
        usage.setdefault("ia_msgs_total", ia_used_today)
        usage.setdefault("ai_messages_total", ia_used_today)
        usage.setdefault("searches_per_month", leads_used)

        remaining = {
            "leads": usage["leads"]["remaining"],
            "csv_exports": usage["csv_exports"]["remaining"],
            "tasks_active": plan.tasks_active_max - tasks_current,
            "ia_msgs": ai_remaining_today,
            "ai_messages": ai_remaining_today,
            "mensajes_ia": ai_remaining_today,
            "tasks": None,
        }

        if plan.type == "free":
            remaining["searches"] = (
                (plan.searches_per_month - leads_used)
                if plan.searches_per_month is not None
                else None
            )
        else:
            remaining["lead_credits"] = (
                (plan.lead_credits_month - leads_used)
                if plan.lead_credits_month is not None
                else None
            )

        result = {
            "plan": plan_name,
            "limits": limits,
            "usage": usage,
            "remaining": remaining,
        }
        return result

    # ------------------------------------------------------------------
    def get_usage(self, user) -> dict:
        return self.get_quotas(user)["usage"]

