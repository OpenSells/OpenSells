from alembic import op
import sqlalchemy as sa


revision = "20260720_add_user_usage_daily"
down_revision = "20260715_fix_lead_info_estado_constraints"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_usage_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period_yyyymmdd", sa.String(), nullable=False),
        sa.Column("ia_msgs", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_user_usage_daily_user_id",
        "user_usage_daily",
        ["user_id"],
    )
    op.create_index(
        "ix_user_usage_daily_period",
        "user_usage_daily",
        ["period_yyyymmdd"],
    )
    op.create_unique_constraint(
        "uix_user_usage_daily",
        "user_usage_daily",
        ["user_id", "period_yyyymmdd"],
    )


def downgrade():
    op.drop_index("ix_user_usage_daily_period", table_name="user_usage_daily")
    op.drop_index("ix_user_usage_daily_user_id", table_name="user_usage_daily")
    op.drop_constraint("uix_user_usage_daily", "user_usage_daily", type_="unique")
    op.drop_table("user_usage_daily")
