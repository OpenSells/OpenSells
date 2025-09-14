import os
from sqlalchemy import text
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_cmd

from .db import engine, has_alembic_version, list_current_tables
from .models import Base

ENABLE_AUTO_BOOTSTRAP = os.getenv("ENABLE_AUTO_BOOTSTRAP", "true").lower() == "true"


def _alembic_cfg():
    cfg = AlembicConfig(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    return cfg


def run_alembic_upgrade_head():
    cfg = _alembic_cfg()
    alembic_cmd.upgrade(cfg, "head")


def run_alembic_stamp_head():
    cfg = _alembic_cfg()
    alembic_cmd.stamp(cfg, "head")


def auto_bootstrap_schema():
    if not ENABLE_AUTO_BOOTSTRAP:
        return

    with engine.begin() as conn:
        conn.execute(text("set search_path to public"))

    try:
        run_alembic_upgrade_head()
        return
    except Exception:
        pass

    with engine.begin() as conn:
        no_version = not has_alembic_version(conn)
        tables = list_current_tables(conn)
        is_fresh_db = len(tables) == 0 or (
            len(tables) == 1 and "alembic_version" in tables
        )

    if no_version or is_fresh_db:
        Base.metadata.create_all(bind=engine)
        run_alembic_stamp_head()
    else:
        pass
