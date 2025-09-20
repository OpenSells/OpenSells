from sqlalchemy import text
from sqlalchemy.orm import Session


def get_table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :t
    """
        ),
        {"t": table_name},
    ).fetchall()
    return {r[0] for r in rows}


def ensure_historial_user_email_lower(db: Session):
    db.execute(text("ALTER TABLE historial ADD COLUMN IF NOT EXISTS user_email_lower TEXT"))
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_historial_user_email_lower ON historial(user_email_lower)"
        )
    )
    db.flush()


def build_historial_insert(db: Session, usuario) -> tuple[str, dict]:
    """
    Devuelve (sql, params_base) para insertar en historial la exportación del usuario.
    El caller debe añadir params_base['filename'] antes de ejecutar.
    """
    cols = get_table_columns(db, "historial")

    if "user_id" in cols:
        sql = "INSERT INTO historial (user_id, filename) VALUES (:uid, :filename)"
        params = {"uid": usuario.id}
        return sql, params

    email_lower = (getattr(usuario, "email", "") or "").lower()

    if "user_email_lower" in cols:
        sql = "INSERT INTO historial (user_email_lower, filename) VALUES (:email_lower, :filename)"
        params = {"email_lower": email_lower}
        return sql, params

    # Fallback: crear columna y usar email_lower
    ensure_historial_user_email_lower(db)
    sql = "INSERT INTO historial (user_email_lower, filename) VALUES (:email_lower, :filename)"
    params = {"email_lower": email_lower}
    return sql, params


__all__ = [
    "get_table_columns",
    "ensure_historial_user_email_lower",
    "build_historial_insert",
]
