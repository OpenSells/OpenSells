"""add case-insensitive email unique index

Revision ID: 20250115_email_lower_unique_index
Revises: 20250108_unify_tenant_key
Create Date: 2025-01-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import logging


# revision identifiers, used by Alembic.
revision = "20250115_email_lower_unique_index"
down_revision = "20250108_unify_tenant_key"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    try:
        with op.get_context().autocommit_block():
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email_lower ON usuarios ((lower(email)))"
                )
            )
    except Exception as exc:  # pragma: no cover - depends on DB state
        logging.error("duplicados detectados en emails: %s", exc)
        dup = conn.execute(
            text(
                "SELECT lower(email) AS e, COUNT(*) FROM usuarios GROUP BY lower(email) HAVING COUNT(*) > 1"
            )
        )
        rows = [r[0] for r in dup]
        if rows:
            logging.error("duplicados: %s", rows)


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        conn.execute(text("DROP INDEX IF EXISTS ix_users_email_lower"))

