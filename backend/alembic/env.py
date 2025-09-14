from __future__ import annotations
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Alembic config
config = context.config

# Logging opcional
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importa metadata de modelos
from backend.models import Base  # ajusta solo si Base vive en otro módulo
target_metadata = Base.metadata

def _get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no está definido en el entorno.")
    return url

def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        # Fuerza schema público para runtime de migraciones
        connection.execute(text("set search_path to public"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
