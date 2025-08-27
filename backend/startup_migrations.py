import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


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
