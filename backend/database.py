import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import inspect, text
import logging
from backend.utils import normalizar_nicho, normalizar_dominio
logger = logging.getLogger(__name__)

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
        with engine.begin() as conn:
            inspector = inspect(conn)
            if "leads_extraidos" in inspector.get_table_names():
                lcols = {c["name"] for c in inspector.get_columns("leads_extraidos")}
                if "dominio" not in lcols:
                    conn.execute(text("ALTER TABLE leads_extraidos ADD COLUMN dominio VARCHAR"))
                conn.execute(
                    text(
                        "UPDATE leads_extraidos SET user_email_lower = LOWER(TRIM(user_email)) "
                        "WHERE user_email_lower IS NULL OR user_email_lower = ''"
                    )
                )
                rows = conn.execute(
                    text(
                        "SELECT id, url, dominio, nicho, nicho_original FROM leads_extraidos"
                    )
                ).fetchall()
                for row in rows:
                    dom = normalizar_dominio(row.url or row.dominio or "")
                    nicho_norm = normalizar_nicho(row.nicho_original or row.nicho or "")
                    updates = {}
                    if not row.dominio or row.dominio != dom:
                        updates["dominio"] = dom
                    if not row.nicho or row.nicho != nicho_norm:
                        updates["nicho"] = nicho_norm
                    if updates:
                        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                        conn.execute(
                            text(f"UPDATE leads_extraidos SET {set_clause} WHERE id = :id"),
                            {**updates, "id": row.id},
                        )
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
            # Constraint de leads se maneja tras crear/normalizar dominio
            "leads_extraidos": ("user_email", None, None),
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
                tcols.add("user_email_lower")
            if src and src in tcols:
                conn.execute(
                    text(
                        f"UPDATE {table} SET user_email_lower = LOWER(TRIM({src})) WHERE user_email_lower IS NULL OR user_email_lower = ''"
                    )
                )
            conn.execute(
                text(f"ALTER TABLE {table} ALTER COLUMN user_email_lower SET NOT NULL")
            )
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

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_leads_user_email_lower ON leads_extraidos(user_email_lower)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_nichos_user_email_lower ON nichos(user_email_lower)"
            )
        )

        # Normalize nichos
        if "nichos" in inspector.get_table_names():
            rows = conn.execute(
                text("SELECT id, nicho, nicho_original FROM nichos")
            ).fetchall()
            for row in rows:
                original = row.nicho_original or row.nicho or ""
                norm = normalizar_nicho(original)
                if not row.nicho or row.nicho != norm:
                    conn.execute(
                        text("UPDATE nichos SET nicho=:n WHERE id=:id"),
                        {"n": norm, "id": row.id},
                    )
            conn.execute(
                text(
                    "UPDATE nichos SET nicho_original = nicho WHERE nicho_original IS NULL OR nicho_original = ''",
                )
            )
            conn.execute(text("ALTER TABLE nichos ALTER COLUMN nicho SET NOT NULL"))
            conn.execute(
                text("ALTER TABLE nichos ALTER COLUMN nicho_original SET NOT NULL")
            )

        # Normalize leads
        if "leads_extraidos" in inspector.get_table_names():
            lcols = {c["name"] for c in inspector.get_columns("leads_extraidos")}
            # Detect alternative domain columns
            dom_col = None
            for cand in ["dominio", "dominio_normalizado", "domain", "host"]:
                if cand in lcols:
                    dom_col = cand
                    break
            if dom_col and dom_col != "dominio":
                logger.info("Renombrando %s a dominio en leads_extraidos", dom_col)
                conn.execute(
                    text(f"ALTER TABLE leads_extraidos RENAME COLUMN {dom_col} TO dominio")
                )
                lcols.add("dominio")
            elif not dom_col:
                logger.info("Adding dominio column to leads_extraidos")
                conn.execute(text("ALTER TABLE leads_extraidos ADD COLUMN dominio VARCHAR"))
                lcols.add("dominio")
            rows = conn.execute(
                text(
                    "SELECT id, url, dominio, nicho, nicho_original FROM leads_extraidos"
                )
            ).fetchall()
            updated_dom = 0
            for row in rows:
                dom = normalizar_dominio(row.url or row.dominio or "")
                nicho_norm = normalizar_nicho(row.nicho_original or row.nicho or "")
                updates = {}
                if not row.dominio or row.dominio != dom:
                    updates["dominio"] = dom
                    updated_dom += 1
                if not row.nicho or row.nicho != nicho_norm:
                    updates["nicho"] = nicho_norm
                if updates:
                    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                    conn.execute(
                        text(f"UPDATE leads_extraidos SET {set_clause} WHERE id = :id"),
                        {**updates, "id": row.id},
                    )
            if updated_dom:
                logger.info("Actualizados %s dominios en leads_extraidos", updated_dom)
            conn.execute(text("ALTER TABLE leads_extraidos ALTER COLUMN dominio SET NOT NULL"))
            conn.execute(text("ALTER TABLE leads_extraidos ALTER COLUMN nicho SET NOT NULL"))
            conn.execute(text("ALTER TABLE leads_extraidos ALTER COLUMN nicho_original SET NOT NULL"))
            uexisting = {
                uc["name"] for uc in inspector.get_unique_constraints("leads_extraidos")
            }
            if "uq_user_dominio" not in uexisting:
                logger.info("Creating unique constraint uq_user_dominio")
                conn.execute(
                    text(
                        "ALTER TABLE leads_extraidos ADD CONSTRAINT uq_user_dominio UNIQUE (user_email_lower, dominio)"
                    )
                )

