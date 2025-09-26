from __future__ import annotations

from datetime import datetime, timezone
import logging
from sqlalchemy import update, func, text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.models import UserUsageMonthly, UserUsageDaily

logger = logging.getLogger(__name__)

MONTHLY_KIND_ALIASES = {
    "searches": "searches",
    "free_searches": "searches",
    "leads": "leads",
    "lead_credits": "leads",
    "lead_credits_month": "leads",
    "ai_messages": "ai_messages",
    "ia_msgs": "ai_messages",
    "mensajes_ia": "ai_messages",
    "tasks": "tasks",
    "csv_exports": "csv_exports",
}

DAILY_KIND_ALIASES = {
    "ai_messages": "ai_messages",
    "ia_msgs": "ai_messages",
    "mensajes_ia": "ai_messages",
}

VALID_KINDS = set(MONTHLY_KIND_ALIASES.keys())
VALID_DAILY_KINDS = set(DAILY_KIND_ALIASES.keys())


def _has_column(model, name: str) -> bool:
    return hasattr(model.__table__.c, name)


class UsageService:
    def __init__(self, db: Session):
        self.db = db
        self._ensure_schema()

    _schema_checked = False

    def _ensure_schema(self) -> None:
        if UsageService._schema_checked:
            return
        try:
            self.db.execute(
                text(
                    "ALTER TABLE user_usage_monthly ADD COLUMN IF NOT EXISTS searches INTEGER DEFAULT 0"
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("usage_schema_check_failed: %s", exc)
        finally:
            UsageService._schema_checked = True

    @staticmethod
    def get_period_yyyymm(dt: datetime | None = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return dt.strftime("%Y%m")

    def ensure_row(self, user_id: int, period: str) -> None:
        values = {
            "user_id": user_id,
            "period_yyyymm": period,
            "leads": 0,
            "ia_msgs": 0,
            "tasks": 0,
            "csv_exports": 0,
        }
        if _has_column(UserUsageMonthly, "searches"):
            values["searches"] = 0
        stmt = pg_insert(UserUsageMonthly).values(**values).on_conflict_do_nothing(
            index_elements=["user_id", "period_yyyymm"]
        )
        self.db.execute(stmt)
        self.db.flush()

    def increment(self, user_id: int, kind: str, amount: int = 1, period: str | None = None) -> None:
        if kind not in VALID_KINDS:
            raise ValueError(f"Invalid usage kind: {kind}")
        period = period or self.get_period_yyyymm()
        self.ensure_row(user_id, period)
        resolved = MONTHLY_KIND_ALIASES.get(kind)
        if not resolved:
            raise ValueError(f"Unsupported usage alias: {kind}")
        column_attr = {
            "leads": UserUsageMonthly.leads,
            "searches": getattr(UserUsageMonthly, "searches", None),
            "ai_messages": UserUsageMonthly.ia_msgs,
            "tasks": UserUsageMonthly.tasks,
            "csv_exports": UserUsageMonthly.csv_exports,
        }.get(resolved)
        if column_attr is None:
            raise ValueError(f"Unsupported usage column for kind={kind}")
        upd = (
            update(UserUsageMonthly)
            .where(
                UserUsageMonthly.user_id == user_id,
                UserUsageMonthly.period_yyyymm == period,
            )
            .values({column_attr.key: column_attr + amount, "updated_at": func.now()})
        )
        self.db.execute(upd)
        self.db.flush()
        logger.info(
            "usage_increment user_id=%s period=%s kind=%s delta=%s",
            user_id,
            period,
            resolved,
            amount,
        )

    def get_usage(self, user_id: int, period: str | None = None) -> dict:
        period = period or self.get_period_yyyymm()
        row = (
            self.db.query(UserUsageMonthly)
            .filter(
                UserUsageMonthly.user_id == user_id,
                UserUsageMonthly.period_yyyymm == period,
            )
            .one_or_none()
        )
        if not row:
            return {
                "leads": 0,
                "searches": 0,
                "ai_messages": 0,
                "ia_msgs": 0,
                "tasks": 0,
                "csv_exports": 0,
            }
        return {
            "leads": row.leads or 0,
            "searches": getattr(row, "searches", 0) or 0,
            "ai_messages": row.ia_msgs or 0,
            "ia_msgs": row.ia_msgs or 0,
            "tasks": row.tasks or 0,
            "csv_exports": row.csv_exports or 0,
        }


class UsageDailyService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_period_yyyymmdd(dt: datetime | None = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return dt.strftime("%Y%m%d")

    def ensure_row(self, user_id: int, period: str) -> None:
        stmt = pg_insert(UserUsageDaily).values(
            user_id=user_id,
            period_yyyymmdd=period,
            ia_msgs=0,
        ).on_conflict_do_nothing(index_elements=["user_id", "period_yyyymmdd"])
        self.db.execute(stmt)
        self.db.flush()

    def increment(self, user_id: int, kind: str, amount: int = 1, period: str | None = None) -> None:
        if kind not in VALID_DAILY_KINDS:
            raise ValueError(f"Invalid daily usage kind: {kind}")
        period = period or self.get_period_yyyymmdd()
        self.ensure_row(user_id, period)
        resolved = DAILY_KIND_ALIASES.get(kind)
        if not resolved:
            raise ValueError(f"Unsupported daily usage alias: {kind}")
        column_attr = UserUsageDaily.ia_msgs
        upd = (
            update(UserUsageDaily)
            .where(
                UserUsageDaily.user_id == user_id,
                UserUsageDaily.period_yyyymmdd == period,
            )
            .values({column_attr.key: column_attr + amount, "updated_at": func.now()})
        )
        self.db.execute(upd)
        self.db.flush()
        logger.info(
            "usage_daily_increment user_id=%s period=%s kind=%s delta=%s",
            user_id,
            period,
            resolved,
            amount,
        )

    def get_usage(self, user_id: int, period: str | None = None) -> dict:
        period = period or self.get_period_yyyymmdd()
        row = (
            self.db.query(UserUsageDaily)
            .filter(
                UserUsageDaily.user_id == user_id,
                UserUsageDaily.period_yyyymmdd == period,
            )
            .one_or_none()
        )
        if not row:
            return {"ai_messages": 0, "ia_msgs": 0}
        value = row.ia_msgs or 0
        return {"ai_messages": value, "ia_msgs": value}


__all__ = ["UsageService", "UsageDailyService", "VALID_KINDS", "VALID_DAILY_KINDS"]
