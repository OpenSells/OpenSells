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


def get_limits(plan_name: str):
    """Return the dataclass with plan limits for the given plan name."""
    return _get_plan_limits(plan_name)


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
        counts = usage_svc.get_usage(user.id, period)
        daily_usage_svc = UsageDailyService(self.db)
        day_period = daily_usage_svc.get_period_yyyymmdd()
        try:
            daily_counts = daily_usage_svc.get_usage(user.id, day_period)
        except Exception as exc:  # noqa: BLE001 - we want to swallow all runtime errors
            logger.warning(
                "daily usage lookup failed user_id=%s period=%s: %s",
                getattr(user, "id", None),
                day_period,
                exc,
                exc_info=exc,
            )
            try:
                self.db.rollback()
            except Exception:
                pass
            daily_counts = {"ia_msgs": 0}

        if not isinstance(daily_counts, dict):
            daily_counts = {"ia_msgs": 0}

        mensajes_ia_today = 0
        seen_ai_keys: set[str] = set()
        for key in ("ia_msgs", "mensajes_ia", "ai_messages", "ia_mensajes"):
            if key in daily_counts and key not in seen_ai_keys:
                try:
                    mensajes_ia_today += int(daily_counts.get(key) or 0)
                except (TypeError, ValueError):
                    continue
                seen_ai_keys.add(key)

        ia_msgs_current = mensajes_ia_today

        ai_remaining_today: int | None
        if plan.ai_daily_limit is None:
            ai_remaining_today = None
        else:
            ai_remaining_today = max(plan.ai_daily_limit - ia_msgs_current, 0)

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
            "leads": {
                "used": counts["leads"],
                "remaining": (plan.lead_credits_month - counts["leads"])
                if plan.lead_credits_month is not None
                else None,
                "period": period,
            },
            "ia_msgs": {
                "used": ia_msgs_current,
                "period": day_period,
                "used_today": ia_msgs_current,
                "remaining_today": ai_remaining_today,
                "limit": plan.ai_daily_limit,
            },
            "ai_messages": {
                "used_today": ia_msgs_current,
                "remaining_today": ai_remaining_today,
                "limit": plan.ai_daily_limit,
                "period": day_period,
            },
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

        if plan.type == "free":
            usage["searches"] = {
                "used": counts["leads"],
                "remaining": (plan.searches_per_month - counts["leads"])
                if plan.searches_per_month is not None
                else None,
                "period": period,
            }
        else:
            usage["lead_credits"] = {
                "used": counts["leads"],
                "remaining": (plan.lead_credits_month - counts["leads"])
                if plan.lead_credits_month is not None
                else None,
                "period": period,
            }

        usage.setdefault("leads_mes", counts["leads"])
        usage["mensajes_ia"] = ia_msgs_current
        usage.setdefault("ia_msgs_total", ia_msgs_current)
        usage.setdefault("ai_messages_total", ia_msgs_current)
        usage.setdefault("searches_per_month", counts["leads"])

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
                (plan.searches_per_month - counts["leads"])
                if plan.searches_per_month is not None
                else None
            )
        else:
            remaining["lead_credits"] = (
                (plan.lead_credits_month - counts["leads"])
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

