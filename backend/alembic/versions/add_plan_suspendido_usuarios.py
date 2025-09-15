"""add plan and suspendido to usuarios"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_plan_suspendido_usuarios"
down_revision = "20260601_merge_parallel_heads"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("usuarios", schema="public")]

    if "plan" not in columns:
        op.add_column(
            "usuarios",
            sa.Column("plan", sa.String(), server_default="free", nullable=False),
            schema="public",
        )

    if "suspendido" not in columns:
        op.add_column(
            "usuarios",
            sa.Column(
                "suspendido",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
            schema="public",
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("usuarios", schema="public")]

    if "suspendido" in columns:
        op.drop_column("usuarios", "suspendido", schema="public")

    if "plan" in columns:
        op.drop_column("usuarios", "plan", schema="public")
