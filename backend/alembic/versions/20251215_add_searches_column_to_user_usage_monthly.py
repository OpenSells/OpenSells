"""Add searches column to user_usage_monthly

Revision ID: 20251215_add_searches_to_usage
Revises: 20251201_create_user_usage_monthly
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251215_add_searches_to_usage'
down_revision = '20251201_create_user_usage_monthly'
branch_labels = None
depends_on = None


def upgrade():
    # ensure searches column exists with default 0 and not null
    op.execute(
        """
        ALTER TABLE user_usage_monthly
        ADD COLUMN IF NOT EXISTS searches INTEGER NOT NULL DEFAULT 0
        """
    )

    # ensure unique constraint on (user_id, period_yyyymm)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uix_user_period'
            ) THEN
                ALTER TABLE user_usage_monthly
                ADD CONSTRAINT uix_user_period UNIQUE (user_id, period_yyyymm);
            END IF;
        END$$;
        """
    )

    # ensure index on user_id
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_usage_monthly_user
        ON user_usage_monthly (user_id);
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_user_usage_monthly_user")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uix_user_period'
            ) THEN
                ALTER TABLE user_usage_monthly DROP CONSTRAINT uix_user_period;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        ALTER TABLE user_usage_monthly
        DROP COLUMN IF EXISTS searches
        """
    )
