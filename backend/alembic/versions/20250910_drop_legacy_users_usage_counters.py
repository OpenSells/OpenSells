"""
Revision ID: 20250910_drop_legacy_users_usage_counters
Revises: 20250201_add_suspendido_column
Create Date: 2025-09-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250910_drop_legacy_users_usage_counters"
down_revision = "20250201_add_suspendido_column"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for tbl in ("users", "usage_counters"):
        bind.execute(
            sa.text(
                "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=:t) THEN "
                "EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(:t) || ' CASCADE'; "
                "END IF; END $$;"
            ),
            {"t": tbl},
        )


def downgrade():
    pass
