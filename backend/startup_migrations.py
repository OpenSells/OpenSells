import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_column(engine: Engine, table: str, column: str, ddl: str) -> None:
    """Ensure a column exists, creating it with provided DDL if missing."""
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c"
            ),
            {"t": table, "c": column},
        ).fetchone()
        if exists:
            return
        conn.execute(text(ddl))
    logger.info("DB schema healed: %s.%s created", table, column)

def ensure_estado_contacto_column(engine: Engine) -> None:
    """Ensure leads_extraidos.estado_contacto exists with safe default."""
    insp = inspect(engine)
    columns = [col["name"] for col in insp.get_columns("leads_extraidos")]
    if "estado_contacto" in columns:
        return

    logger.warning("Columna estado_contacto ausente; creando en leads_extraidos")
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE leads_extraidos "
                "ADD COLUMN estado_contacto VARCHAR(20) NOT NULL DEFAULT 'pendiente'"
            )
        )
    logger.info("Columna estado_contacto creada")


def ensure_lead_tarea_auto_column(engine: Engine) -> None:
    """Ensure lead_tarea.auto exists with safe default."""
    insp = inspect(engine)
    columns = [col["name"] for col in insp.get_columns("lead_tarea")]
    if "auto" in columns:
        return

    logger.warning("Columna auto ausente; creando en lead_tarea")
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE lead_tarea "
                "ADD COLUMN auto BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
    logger.info("Columna auto creada")
