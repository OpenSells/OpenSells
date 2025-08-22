import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# Load environment variables as early as possible
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no está definido. Verifica tu configuración")

url = make_url(DATABASE_URL)
connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if url.drivername.startswith("sqlite"):
    # In-memory or file-based SQLite for local/tests
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["poolclass"] = StaticPool
else:
    # Assume PostgreSQL/Render deployment
    if "sslmode" not in url.query:
        connect_args["sslmode"] = "require"
    engine_kwargs.update(
        {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "connect_args": connect_args,
        }
    )

engine = create_engine(url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_info() -> dict:
    """Return a summary of the current DB configuration."""
    return {
        "driver": url.drivername,
        "host": url.host,
        "database": url.database,
        "sslmode": connect_args.get("sslmode") or url.query.get("sslmode"),
    }

