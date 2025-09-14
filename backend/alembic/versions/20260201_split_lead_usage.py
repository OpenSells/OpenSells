from alembic import op


revision = "20260201_split_lead_usage"
down_revision = "20260101_add_user_usage_monthly"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE user_usage_monthly
          ADD COLUMN IF NOT EXISTS free_searches integer NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS lead_credits integer NOT NULL DEFAULT 0
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_uum_user_period
          ON user_usage_monthly (user_id, period_yyyymm)
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_uum_user_period")
    # op.execute("ALTER TABLE user_usage_monthly DROP COLUMN IF EXISTS free_searches")
    # op.execute("ALTER TABLE user_usage_monthly DROP COLUMN IF EXISTS lead_credits")

