from alembic import op
import sqlalchemy as sa

revision = '20260101_add_user_usage_monthly'
down_revision = '20251201_create_usage_counters'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_usage_monthly (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            period_yyyymm VARCHAR NOT NULL,
            leads INTEGER DEFAULT 0,
            ia_msgs INTEGER DEFAULT 0,
            tasks INTEGER DEFAULT 0,
            csv_exports INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_user_usage_monthly
        ON user_usage_monthly(user_id, period_yyyymm)
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS user_usage_monthly")
