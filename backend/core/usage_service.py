from __future__ import annotations

from datetime import datetime, timezone
import logging
from sqlalchemy import update, func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import ProgrammingError, OperationalError

try:
    from psycopg2.errors import UndefinedTable
except Exception:  # pragma: no cover - psycopg2 not installed in some envs
    UndefinedTable = None

from backend.models import UserUsageMonthly, UserUsageDaily

logger = logging.getLogger(__name__)

VALID_KINDS = {"leads", "ia_msgs", "tasks", "csv_exports"}
VALID_DAILY_KINDS = {"ia_msgs"}


class UsageService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_period_yyyymm(dt: datetime | None = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return dt.strftime("%Y%m")

    def ensure_row(self, user_id: int, period: str) -> None:
        stmt = pg_insert(UserUsageMonthly).values(
            user_id=user_id,
            period_yyyymm=period,
            leads=0,
            ia_msgs=0,
            tasks=0,
            csv_exports=0,
        ).on_conflict_do_nothing(index_elements=["user_id", "period_yyyymm"])
        self.db.execute(stmt)
        self.db.flush()

    def increment(self, user_id: int, kind: str, amount: int = 1, period: str | None = None) -> None:
        if kind not in VALID_KINDS:
            raise ValueError(f"Invalid usage kind: {kind}")
        period = period or self.get_period_yyyymm()
        self.ensure_row(user_id, period)
        col = getattr(UserUsageMonthly, kind)
        upd = (
            update(UserUsageMonthly)
            .where(
                UserUsageMonthly.user_id == user_id,
                UserUsageMonthly.period_yyyymm == period,
            )
            .values({kind: col + amount, "updated_at": func.now()})
        )
        self.db.execute(upd)
        self.db.flush()
        logger.info(
            "usage_increment user_id=%s period=%s kind=%s delta=%s",
            user_id,
            period,
            kind,
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
            return {"leads": 0, "ia_msgs": 0, "tasks": 0, "csv_exports": 0}
        return {
            "leads": row.leads or 0,
            "ia_msgs": row.ia_msgs or 0,
            "tasks": row.tasks or 0,
            "csv_exports": row.csv_exports or 0,
        }


class UsageDailyService:
    def __init__(self, db: Session):
        self.db = db
        self._missing_table_warned = False

    @staticmethod
    def get_period_yyyymmdd(dt: datetime | None = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return dt.strftime("%Y%m%d")

    def _is_missing_table_error(self, exc: Exception) -> bool:
        if UndefinedTable is not None and isinstance(exc, UndefinedTable):
            return True
        orig = getattr(exc, "orig", None)
        if UndefinedTable is not None and isinstance(orig, UndefinedTable):
            return True
        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "42P01":  # undefined_table in PostgreSQL
            return True
        message = str(exc).lower()
        return "undefined table" in message and "user_usage_daily" in message

    def _handle_missing_table(self, exc: Exception | None = None) -> dict:
        try:
            self.db.rollback()
        except Exception:
            pass
        if not self._missing_table_warned:
            logger.warning("user_usage_daily missing; returning zeros")
            self._missing_table_warned = True
        return {"ia_msgs": 0}

    def ensure_row(self, user_id: int, period: str) -> None:
        self.get_or_create_daily(user_id, period)

    def get_or_create_daily(self, user_id: int, period: str | None = None) -> dict:
        period = period or self.get_period_yyyymmdd()
        stmt = pg_insert(UserUsageDaily).values(
            user_id=user_id,
            period_yyyymmdd=period,
            ia_msgs=0,
        ).on_conflict_do_nothing(index_elements=["user_id", "period_yyyymmdd"])
        try:
            self.db.execute(stmt)
            self.db.flush()
        except (ProgrammingError, OperationalError) as exc:
            if self._is_missing_table_error(exc):
                return self._handle_missing_table(exc)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            if self._is_missing_table_error(exc):
                return self._handle_missing_table(exc)
            raise
        return self.get_usage(user_id, period)

    def increment(self, user_id: int, kind: str, amount: int = 1, period: str | None = None) -> None:
        if kind not in VALID_DAILY_KINDS:
            raise ValueError(f"Invalid daily usage kind: {kind}")
        period = period or self.get_period_yyyymmdd()
        self.get_or_create_daily(user_id, period)
        if self._missing_table_warned:
            return
        col = getattr(UserUsageDaily, kind)
        upd = (
            update(UserUsageDaily)
            .where(
                UserUsageDaily.user_id == user_id,
                UserUsageDaily.period_yyyymmdd == period,
            )
            .values({kind: col + amount, "updated_at": func.now()})
        )
        try:
            self.db.execute(upd)
            self.db.flush()
        except (ProgrammingError, OperationalError) as exc:
            if self._is_missing_table_error(exc):
                self._handle_missing_table(exc)
                return
            raise
        except Exception as exc:  # pragma: no cover - defensive
            if self._is_missing_table_error(exc):
                self._handle_missing_table(exc)
                return
            raise
        logger.info(
            "usage_daily_increment user_id=%s period=%s kind=%s delta=%s",
            user_id,
            period,
            kind,
            amount,
        )

    def get_usage(self, user_id: int, period: str | None = None) -> dict:
        period = period or self.get_period_yyyymmdd()
        try:
            row = (
                self.db.query(UserUsageDaily)
                .filter(
                    UserUsageDaily.user_id == user_id,
                    UserUsageDaily.period_yyyymmdd == period,
                )
                .one_or_none()
            )
        except (ProgrammingError, OperationalError) as exc:
            if self._is_missing_table_error(exc):
                return self._handle_missing_table(exc)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            if self._is_missing_table_error(exc):
                return self._handle_missing_table(exc)
            raise
        if not row:
            return {"ia_msgs": 0}
        return {"ia_msgs": row.ia_msgs or 0}


__all__ = ["UsageService", "UsageDailyService", "VALID_KINDS", "VALID_DAILY_KINDS"]
