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
        usage_svc = UsageService(self.db)
        period = usage_svc.get_period_yyyymm()
        counts = usage_svc.get_usage(user.id, period)

        used_leads = (
            counts["free_searches"] if plan.type == "free" else counts["lead_credits"]
        )
        remaining_leads = (
            plan.searches_per_month - used_leads
            if plan.type == "free"
            else (
                (plan.lead_credits_month - used_leads)
                if plan.lead_credits_month is not None
                else None
            )
        )

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
            "leads": {"used": used_leads, "remaining": remaining_leads, "period": period},
            "free_searches": {"used": counts["free_searches"], "period": period},
            "lead_credits": {"used": counts["lead_credits"], "period": period},
            "ia_msgs": {"used": counts["ia_msgs"], "period": period},
            "tasks": {"used": counts["tasks"], "period": period},
            "csv_exports": {
                "used": counts["csv_exports"],
                "remaining": (plan.csv_exports_per_month - counts["csv_exports"])
                if plan.csv_exports_per_month is not None
                else None,
                "period": period,
            },
            "tasks_active": {"current": tasks_current, "limit": plan.tasks_active_max},
        }

        remaining = {
            "leads": remaining_leads,
            "csv_exports": usage["csv_exports"]["remaining"],
            "tasks_active": plan.tasks_active_max - tasks_current,
            "ia_msgs": None,
            "tasks": None,
        }

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

