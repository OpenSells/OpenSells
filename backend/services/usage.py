from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.models import UsageCounter


class UsageCounterService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_current_period_date(dt: datetime | None = None) -> date:
        dt = dt or datetime.utcnow()
        return dt.replace(day=1).date()

    def get_or_create_usage(self, user_id: int, period_month: date | None = None) -> UsageCounter:
        period_month = period_month or self.get_current_period_date()
        stmt = (
            pg_insert(UsageCounter)
            .values(
                user_id=user_id,
                period_month=period_month,
                leads_used=0,
                searches_used=0,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "period_month"],
                set_={"updated_at": func.now()},
            )
            .returning(UsageCounter)
        )
        row = self.db.execute(stmt).scalar_one()
        self.db.flush()
        return row

    def increment_leads(self, user_id: int, amount: int = 1) -> UsageCounter:
        period = self.get_current_period_date()
        stmt = (
            pg_insert(UsageCounter)
            .values(
                user_id=user_id,
                period_month=period,
                leads_used=amount,
                searches_used=0,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "period_month"],
                set_={
                    "leads_used": UsageCounter.leads_used + amount,
                    "updated_at": func.now(),
                },
            )
            .returning(UsageCounter)
        )
        row = self.db.execute(stmt).scalar_one()
        self.db.flush()
        return row

    def increment_searches(self, user_id: int, amount: int = 1) -> UsageCounter:
        period = self.get_current_period_date()
        stmt = (
            pg_insert(UsageCounter)
            .values(
                user_id=user_id,
                period_month=period,
                leads_used=0,
                searches_used=amount,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "period_month"],
                set_={
                    "searches_used": UsageCounter.searches_used + amount,
                    "updated_at": func.now(),
                },
            )
            .returning(UsageCounter)
        )
        row = self.db.execute(stmt).scalar_one()
        self.db.flush()
        return row

    def get_usage(self, user_id: int, period_month: date | None = None) -> UsageCounter | None:
        period_month = period_month or self.get_current_period_date()
        stmt = select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.period_month == period_month,
        )
        return self.db.execute(stmt).scalar_one_or_none()
