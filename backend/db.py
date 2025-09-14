import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL")
ENGINE_OPTS = dict(pool_pre_ping=True, future=True)
CONNECT_ARGS = {"options": "-csearch_path=public"}

engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS, **ENGINE_OPTS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def has_alembic_version(conn) -> bool:
    try:
        return (
            conn.execute(
                text(
                    "select 1 from information_schema.tables "
                    "where table_schema=current_schema() and table_name='alembic_version'"
                )
            ).first()
            is not None
        )
    except Exception:
        return False

def list_current_tables(conn):
    return [
        r[0]
        for r in conn.execute(
            text(
                "select table_name from information_schema.tables "
                "where table_schema=current_schema()"
            )
        ).fetchall()
    ]
