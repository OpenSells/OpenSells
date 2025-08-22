import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import inspect, text

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


def bootstrap_database():
    """Idempotent database fixes for production (adds columns/constraints)."""
    if url.drivername.startswith("sqlite"):
        return
    with engine.begin() as conn:
        inspector = inspect(conn)
        # usuarios.email_lower
        cols = {c["name"] for c in inspector.get_columns("usuarios")}
        if "email_lower" not in cols:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN email_lower VARCHAR"))
        conn.execute(text(
            "UPDATE usuarios SET email_lower = LOWER(TRIM(email)) WHERE email_lower IS NULL OR email_lower = ''"
        ))
        conn.execute(text("ALTER TABLE usuarios ALTER COLUMN email_lower SET NOT NULL"))
        ucs = {uc["name"] for uc in inspector.get_unique_constraints("usuarios")}
        if "ux_usuarios_email_lower" not in ucs:
            conn.execute(text(
                "ALTER TABLE usuarios ADD CONSTRAINT ux_usuarios_email_lower UNIQUE (email_lower)"
            ))
        # plan column default/backfill
        if "plan" not in cols:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN plan VARCHAR DEFAULT 'free'"))
        else:
            conn.execute(text("ALTER TABLE usuarios ALTER COLUMN plan SET DEFAULT 'free'"))
        conn.execute(text("UPDATE usuarios SET plan='free' WHERE plan IS NULL OR plan=''"))
        conn.execute(text("ALTER TABLE usuarios ALTER COLUMN plan SET NOT NULL"))

        # Ensure user_email_lower columns and uniqueness
        table_sources = {
            "nichos": ("email", "uq_user_nicho", "nicho"),
            "leads_extraidos": ("user_email", "uq_user_url", "url"),
            "lead_tarea": ("email", None, None),
            "lead_historial": ("email", None, None),
            "lead_info_extra": ("user_email", None, None),
            "suscripciones": (None, None, None),
        }
        for table, (src, uq_name, uq_col) in table_sources.items():
            if table not in inspector.get_table_names():
                continue
            tcols = {c["name"] for c in inspector.get_columns(table)}
            if "user_email_lower" not in tcols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_email_lower VARCHAR"))
                if src and src in tcols:
                    conn.execute(text(
                        f"UPDATE {table} SET user_email_lower = LOWER(TRIM({src})) WHERE user_email_lower IS NULL"
                    ))
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN user_email_lower SET NOT NULL"))
            idxs = {idx["name"] for idx in inspector.get_indexes(table)}
            idx_name = f"ix_{table}_user_email_lower"
            if idx_name not in idxs:
                conn.execute(text(f"CREATE INDEX {idx_name} ON {table}(user_email_lower)"))
            if uq_name and uq_col:
                uexisting = {uc["name"] for uc in inspector.get_unique_constraints(table)}
                if uq_name not in uexisting:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD CONSTRAINT {uq_name} UNIQUE (user_email_lower, {uq_col})"
                    ))

