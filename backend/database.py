from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# ✅ Cargar archivo .env manualmente desde la raíz del proyecto
dotenv_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no está definido. Verifica tu archivo .env")

if DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite no soportado. Configure PostgreSQL en DATABASE_URL.")

url_obj = make_url(DATABASE_URL)
if url_obj.drivername.startswith("postgresql") and "sslmode" not in url_obj.query:
    url_obj = url_obj.set(query={**url_obj.query, "sslmode": "require"})
    DATABASE_URL = url_obj.render_as_string(hide_password=False)

MASKED_DSN = (
    f"{url_obj.drivername}://***:***@{url_obj.host}:{url_obj.port}/{url_obj.database}"
    + ("?" + "&".join(f"{k}={v}" for k, v in url_obj.query.items()) if url_obj.query else "")
)

logging.info("DB → %s", MASKED_DSN)

# ✅ Crear engine síncrono
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
