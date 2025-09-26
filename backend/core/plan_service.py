from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Tuple

from sqlalchemy.orm import Session

from backend.core.plan_config import PLANES, get_limits as _get_plan_limits
from backend.core.stripe_mapping import stripe_price_to_plan
from backend.core.usage_service import UsageService, UsageDailyService
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
        period_month = usage_svc.get_period_yyyymm()
        monthly_counts = usage_svc.get_usage(user.id, period_month)
        daily_usage_svc = UsageDailyService(self.db)
        period_day = daily_usage_svc.get_period_yyyymmdd()
        daily_counts = daily_usage_svc.get_usage(user.id, period_day)

        tasks_current = (
            self.db.query(LeadTarea)
            .filter(
                LeadTarea.user_email_lower == user.email_lower,
                LeadTarea.completado.is_(False),
            )
            .count()
        )

        def _normalize_limit(value):
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _coalesce_count(source: dict, *keys: str) -> int:
            for key in keys:
                value = source.get(key)
                if value is None:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
            return 0

        searches_used = _coalesce_count(
            monthly_counts,
            "searches",
            "free_searches",
            "searches_per_month",
            "searches_month",
        )
        leads_used = _coalesce_count(
            monthly_counts,
            "leads",
            "lead_credits",
            "lead_credits_month",
        )
        ai_used_today = _coalesce_count(daily_counts, "ai_messages", "ia_msgs", "mensajes_ia")

        searches_limit = _normalize_limit(plan.searches_per_month)
        leads_cap_per_search = _normalize_limit(plan.leads_cap_per_search)
        if plan.lead_credits_month is not None:
            leads_limit = _normalize_limit(plan.lead_credits_month)
        elif searches_limit is not None and leads_cap_per_search is not None:
            leads_limit = searches_limit * leads_cap_per_search
        else:
            leads_limit = None

        csv_limit = _normalize_limit(getattr(plan, "csv_exports_per_month", None))
        limits = {
            "searches_per_month": searches_limit,
            "lead_credits_month": leads_limit,
            "ai_daily_limit": _normalize_limit(plan.ai_daily_limit),
            "tasks_active_max": _normalize_limit(plan.tasks_active_max),
            "leads_cap_per_search": leads_cap_per_search,
        }
        limits["csv_exports_per_month"] = csv_limit
        limits["csv_rows_cap_free"] = _normalize_limit(
            getattr(plan, "csv_rows_cap_free", None)
        )

        def _remaining(limit: int | None, used: int) -> int | None:
            if limit is None:
                return None
            return max(limit - used, 0)

        csv_used = _coalesce_count(monthly_counts, "csv_exports")
        remaining = {
            "searches": _remaining(limits["searches_per_month"], searches_used),
            "lead_credits": _remaining(leads_limit, leads_used),
            "ai_messages": _remaining(limits["ai_daily_limit"], ai_used_today),
            "tasks_active": _remaining(limits["tasks_active_max"], tasks_current),
        }
        remaining["csv_exports"] = _remaining(csv_limit, csv_used)
        remaining["leads"] = remaining["lead_credits"]
        remaining["ia_msgs"] = remaining["ai_messages"]

        usage = {
            "searches": searches_used,
            "leads_used": leads_used,
            "mensajes_ia": ai_used_today,
            "tasks_active": {
                "current": tasks_current,
                "limit": limits["tasks_active_max"],
            },
        }

        # Backwards compatible payload (legacy keys expected by other callers)
        usage["ai_messages"] = {
            "used_today": ai_used_today,
            "remaining_today": remaining["ai_messages"],
            "period": period_day,
        }
        usage["ia_msgs"] = {"used": ai_used_today, "period": period_day}
        usage["tasks_active"].update({"remaining": remaining["tasks_active"]})
        usage["csv_exports"] = {
            "used": csv_used,
            "remaining": remaining["csv_exports"],
            "period": period_month,
        }
        usage["leads"] = {
            "used": leads_used,
            "remaining": remaining["lead_credits"],
            "period": period_month,
        }
        if plan.type == "free":
            usage["free_searches"] = {
                "used": searches_used,
                "remaining": remaining["searches"],
                "period": period_month,
            }
        else:
            usage["lead_credits"] = {
                "used": leads_used,
                "remaining": remaining["lead_credits"],
                "period": period_month,
            }

        result = {
            "plan": plan_name,
            "limits": limits,
            "usage": usage,
            "remaining": remaining,
            "period": {"month": period_month, "ai_day": period_day},
        }
        return result

    # ------------------------------------------------------------------
    def get_usage(self, user) -> dict:
        return self.get_quotas(user)["usage"]

