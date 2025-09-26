"""create lead_historial table"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250926_add_lead_historial"
down_revision = "20250910_drop_legacy_users_usage_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_historial",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("user_email_lower", sa.Text(), nullable=False),
        sa.Column("dominio", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_lead_historial_user",
        "lead_historial",
        ["user_email_lower"],
    )
    op.create_index("idx_lead_historial_tipo", "lead_historial", ["tipo"])
    op.create_index("idx_lead_historial_dominio", "lead_historial", ["dominio"])
    op.create_index("idx_lead_historial_ts", "lead_historial", ["timestamp"])


def downgrade() -> None:
    op.drop_index("idx_lead_historial_ts", table_name="lead_historial")
    op.drop_index("idx_lead_historial_dominio", table_name="lead_historial")
    op.drop_index("idx_lead_historial_tipo", table_name="lead_historial")
    op.drop_index("idx_lead_historial_user", table_name="lead_historial")
    op.drop_table("lead_historial")
