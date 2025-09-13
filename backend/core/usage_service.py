from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import insert, update, func
from sqlalchemy.orm import Session

from backend.models import UserUsageMonthly

logger = logging.getLogger(__name__)


class UsageService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_period_yyyymm(dt: datetime | None = None) -> str:
        dt = dt or datetime.utcnow()
        return dt.strftime("%Y%m")

    # ------------------------------------------------------------------
    def ensure_row(self, user_id: int, period: str | None = None) -> None:
        period = period or self.get_period_yyyymm()
        stmt = (
            insert(UserUsageMonthly)
            .values(user_id=user_id, period_yyyymm=period)
            .on_conflict_do_nothing(index_elements=["user_id", "period_yyyymm"])
        )
        self.db.execute(stmt)
        self.db.commit()

    # ------------------------------------------------------------------
    def increment(self, user_id: int, kind: str, amount: int = 1) -> int:
        period = self.get_period_yyyymm()
        self.ensure_row(user_id, period)
        if not hasattr(UserUsageMonthly, kind):
            raise ValueError(f"Invalid usage kind: {kind}")
        col = getattr(UserUsageMonthly, kind)
        stmt = (
            update(UserUsageMonthly)
            .where(
                UserUsageMonthly.user_id == user_id,
                UserUsageMonthly.period_yyyymm == period,
            )
            .values({kind: col + amount, "updated_at": func.now()})
            .returning(col + amount)
        )
        res = self.db.execute(stmt)
        self.db.commit()
        new_val = res.scalar() or 0
        logger.info(
            "usage_increment user_id=%s period=%s kind=%s delta=%s new_value=%s",
            user_id,
            period,
            kind,
            amount,
            new_val,
        )
        return new_val

    # ------------------------------------------------------------------
    def get_usage(self, user_id: int, period: str | None = None) -> dict:
        period = period or self.get_period_yyyymm()
        row = (
            self.db.query(UserUsageMonthly)
            .filter(
                UserUsageMonthly.user_id == user_id,
                UserUsageMonthly.period_yyyymm == period,
            )
            .first()
        )
        if not row:
            return {"leads": 0, "ia_msgs": 0, "tasks": 0, "csv_exports": 0}
        return {
            "leads": row.leads,
            "ia_msgs": row.ia_msgs,
            "tasks": row.tasks,
            "csv_exports": row.csv_exports,
        }


__all__ = ["UsageService"]
