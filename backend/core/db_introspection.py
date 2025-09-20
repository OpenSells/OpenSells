"""Helpers de introspección de base de datos para columnas dinámicas."""
from __future__ import annotations

from typing import Set, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_table_columns(db: Session, table_name: str) -> Set[str]:
    """Devuelve el conjunto de columnas existentes para ``table_name``."""
    result = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return {row[0] for row in result}


def ensure_historial_user_email_lower(db: Session) -> None:
    """Garantiza la existencia de la columna ``user_email_lower`` en ``historial``."""
    db.execute(
        text("ALTER TABLE historial ADD COLUMN IF NOT EXISTS user_email_lower TEXT")
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_historial_user_email_lower ON historial(user_email_lower)"
        )
    )
    db.flush()


def _get_email_lower(usuario) -> str:
    email_lower = getattr(usuario, "user_email_lower", None)
    if email_lower:
        return email_lower
    email = getattr(usuario, "email", "") or ""
    return email.strip().lower()


def historial_insert_params(db: Session, usuario) -> Tuple[str, dict, bool]:
    """Determina el ``INSERT`` adecuado para ``historial`` y sus parámetros.

    Devuelve una tupla ``(sql, params, has_id_column)`` donde ``has_id_column``
    indica si la tabla posee una columna ``id`` para usar en ``RETURNING``.
    """

    columns = get_table_columns(db, "historial")
    has_id = "id" in columns
    email_lower = _get_email_lower(usuario)

    if "user_id" in columns:
        sql = "INSERT INTO historial (user_id, filename) VALUES (:uid, :filename)"
        params = {"uid": getattr(usuario, "id", None), "filename": None}
        return sql, params, has_id

    if "user_email_lower" in columns:
        sql = (
            "INSERT INTO historial (user_email_lower, filename) VALUES (:email_lower, :filename)"
        )
        params = {"email_lower": email_lower, "filename": None}
        return sql, params, has_id

    ensure_historial_user_email_lower(db)
    sql = "INSERT INTO historial (user_email_lower, filename) VALUES (:email_lower, :filename)"
    params = {"email_lower": email_lower, "filename": None}
    # Tras el ALTER TABLE asumimos que sigue existiendo la columna id si antes estaba
    return sql, params, has_id


__all__ = [
    "get_table_columns",
    "ensure_historial_user_email_lower",
    "historial_insert_params",
]
