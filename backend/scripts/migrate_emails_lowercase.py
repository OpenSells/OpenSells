"""Migra campos de email a minúsculas y popula user_email_lower.

Uso:
    python backend/scripts/migrate_emails_lowercase.py
"""
from sqlalchemy import text
from backend.database import engine

STEPS = [
    # 2.1 Añadir columnas auxiliares si no existen
    """
    ALTER TABLE leads_extraidos ADD COLUMN IF NOT EXISTS user_email_lower TEXT;
    ALTER TABLE lead_tarea ADD COLUMN IF NOT EXISTS user_email_lower TEXT;
    ALTER TABLE lead_historial ADD COLUMN IF NOT EXISTS user_email_lower TEXT;
    ALTER TABLE lead_nota ADD COLUMN IF NOT EXISTS user_email_lower TEXT;
    ALTER TABLE lead_info_extra ADD COLUMN IF NOT EXISTS user_email_lower TEXT;
    """,
    # 2.2 Backfill idempotente
    """
    UPDATE leads_extraidos SET user_email_lower = LOWER(user_email)
    WHERE user_email_lower IS NULL AND user_email IS NOT NULL;
    UPDATE lead_tarea SET user_email_lower = LOWER(email)
    WHERE user_email_lower IS NULL AND email IS NOT NULL;
    UPDATE lead_historial SET user_email_lower = LOWER(email)
    WHERE user_email_lower IS NULL AND email IS NOT NULL;
    UPDATE lead_nota SET user_email_lower = LOWER(email)
    WHERE user_email_lower IS NULL AND email IS NOT NULL;
    UPDATE lead_info_extra SET user_email_lower = LOWER(user_email)
    WHERE user_email_lower IS NULL AND user_email IS NOT NULL;
    """,
    # 2.3 Índices
    """
    CREATE INDEX IF NOT EXISTS ix_leads_user_lower ON leads_extraidos (user_email_lower);
    CREATE INDEX IF NOT EXISTS ix_tareas_user_lower ON lead_tarea (user_email_lower);
    CREATE INDEX IF NOT EXISTS ix_hist_user_lower ON lead_historial (user_email_lower);
    CREATE INDEX IF NOT EXISTS ix_nota_user_lower ON lead_nota (user_email_lower);
    CREATE INDEX IF NOT EXISTS ix_info_user_lower ON lead_info_extra (user_email_lower);
    """,
]

def main():
    with engine.begin() as conn:
        for step in STEPS:
            for stmt in filter(None, step.strip().split(";")):
                conn.execute(text(stmt))

if __name__ == "__main__":
    main()

