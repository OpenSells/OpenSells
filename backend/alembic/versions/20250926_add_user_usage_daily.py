"""create user_usage_daily table"""

from alembic import op
import sqlalchemy as sa


revision = "20250926_add_user_usage_daily"
down_revision = "20250910_drop_legacy_users_usage_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_usage_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_yyyymmdd", sa.String(length=8), nullable=False),
        sa.Column("ia_msgs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "period_yyyymmdd", name="uix_user_usage_daily"),
    )
    op.create_index(
        "ix_user_usage_daily_user_period",
        "user_usage_daily",
        ["user_id", "period_yyyymmdd"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_usage_daily_user_period", table_name="user_usage_daily")
    op.drop_table("user_usage_daily")
