"""Ensure usage tables exist"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250927_ensure_usage_tables"
down_revision = (
    "20260715_fix_lead_info_estado_constraints",
    "20250926_add_user_usage_daily",
)
branch_labels = None
depends_on = None


DAILY_SQL = """
CREATE TABLE IF NOT EXISTS user_usage_daily (
  id BIGSERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  period_yyyymmdd VARCHAR(8) NOT NULL,
  ia_msgs INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_usage_daily_user_period_uk UNIQUE (user_id, period_yyyymmdd)
);

CREATE INDEX IF NOT EXISTS idx_user_usage_daily_user ON user_usage_daily(user_id);
CREATE INDEX IF NOT EXISTS idx_user_usage_daily_period ON user_usage_daily(period_yyyymmdd);
"""


MONTHLY_SQL = """
CREATE TABLE IF NOT EXISTS user_usage_monthly (
  id BIGSERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  period_yyyymm VARCHAR(6) NOT NULL,
  leads INTEGER NOT NULL DEFAULT 0,
  ia_msgs INTEGER NOT NULL DEFAULT 0,
  tasks INTEGER NOT NULL DEFAULT 0,
  csv_exports INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_usage_monthly_user_period_uk UNIQUE (user_id, period_yyyymm)
);

CREATE INDEX IF NOT EXISTS idx_user_usage_monthly_user ON user_usage_monthly(user_id);
CREATE INDEX IF NOT EXISTS idx_user_usage_monthly_period ON user_usage_monthly(period_yyyymm);
"""


def upgrade() -> None:
    op.execute(DAILY_SQL)
    op.execute(MONTHLY_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_usage_daily CASCADE")
    op.execute("DROP TABLE IF EXISTS user_usage_monthly CASCADE")
