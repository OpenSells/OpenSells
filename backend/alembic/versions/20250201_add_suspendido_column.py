"""add suspendido column to usuarios

Revision ID: 20250201_add_suspendido_column
Revises: 20250115_email_lower_unique_index
Create Date: 2025-02-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20250201_add_suspendido_column"
down_revision = "20250115_email_lower_unique_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        with op.get_context().autocommit_block():
            conn.execute(
                text(
                    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS suspendido BOOLEAN"
                )
            )
            conn.execute(text("UPDATE usuarios SET suspendido = FALSE WHERE suspendido IS NULL"))
            conn.execute(
                text(
                    "ALTER TABLE usuarios ALTER COLUMN suspendido SET DEFAULT FALSE"
                )
            )
            conn.execute(
                text("ALTER TABLE usuarios ALTER COLUMN suspendido SET NOT NULL")
            )
    else:  # SQLite and others
        with op.batch_alter_table("usuarios", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "suspendido",
                    sa.Boolean(),
                    server_default=sa.text("0"),
                    nullable=False,
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            conn.execute(text("ALTER TABLE usuarios DROP COLUMN IF EXISTS suspendido"))
    else:
        with op.batch_alter_table("usuarios", schema=None) as batch_op:
            batch_op.drop_column("suspendido")
