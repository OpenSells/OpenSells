"""Ensure lead info/estado uniqueness and schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "20260715_fix_lead_info_estado_constraints"
down_revision = "20260601_merge_parallel_heads"
branch_labels = None
depends_on = None


def _ensure_lead_info_extra(bind):
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "lead_info_extra" not in tables:
        op.create_table(
            "lead_info_extra",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_email_lower", sa.Text, nullable=False),
            sa.Column("dominio", sa.Text, nullable=False),
            sa.Column("email", sa.Text, nullable=True),
            sa.Column("telefono", sa.Text, nullable=True),
            sa.Column("informacion", sa.Text, nullable=True),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "user_email_lower",
                "dominio",
                name="uix_lead_info_extra_usuario_dominio",
            ),
        )
        op.create_index(
            "ix_lead_info_extra_user_email_lower",
            "lead_info_extra",
            ["user_email_lower"],
        )
        op.create_index(
            "ix_lead_info_extra_dominio",
            "lead_info_extra",
            ["dominio"],
        )
        return

    with bind.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM lead_info_extra a
                USING lead_info_extra b
                WHERE a.ctid < b.ctid
                  AND a.user_email_lower IS NOT DISTINCT FROM b.user_email_lower
                  AND a.dominio IS NOT DISTINCT FROM b.dominio
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_info_extra
                   SET user_email_lower = CONCAT('__legacy_user__:', id)
                 WHERE user_email_lower IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_info_extra
                   SET dominio = CONCAT('__legacy_domain__:', id)
                 WHERE dominio IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_info_extra
                   SET timestamp = NOW()
                 WHERE timestamp IS NULL
                """
            )
        )

    inspector = inspect(bind)
    columns = {col["name"]: col for col in inspector.get_columns("lead_info_extra")}
    if "user_email_lower" not in columns:
        op.add_column(
            "lead_info_extra",
            sa.Column("user_email_lower", sa.Text, nullable=False, server_default=""),
        )
        op.execute(
            text(
                "UPDATE lead_info_extra SET user_email_lower = CONCAT('__legacy_user__:', id) WHERE user_email_lower = ''"
            )
        )
        op.alter_column(
            "lead_info_extra",
            "user_email_lower",
            server_default=None,
            existing_type=sa.Text(),
            nullable=False,
        )
    else:
        op.alter_column(
            "lead_info_extra",
            "user_email_lower",
            existing_type=columns["user_email_lower"]["type"],
            nullable=False,
        )

    if "dominio" not in columns:
        op.add_column(
            "lead_info_extra",
            sa.Column("dominio", sa.Text, nullable=False, server_default="__legacy_domain__"),
        )
        op.execute(
            text(
                "UPDATE lead_info_extra SET dominio = CONCAT('__legacy_domain__:', id) WHERE dominio = '__legacy_domain__'"
            )
        )
        op.alter_column(
            "lead_info_extra",
            "dominio",
            existing_type=sa.Text(),
            nullable=False,
            server_default=None,
        )
    else:
        op.alter_column(
            "lead_info_extra",
            "dominio",
            existing_type=columns["dominio"]["type"],
            nullable=False,
        )

    if "timestamp" not in columns:
        op.add_column(
            "lead_info_extra",
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    else:
        op.alter_column(
            "lead_info_extra",
            "timestamp",
            existing_type=columns["timestamp"]["type"],
            nullable=False,
            server_default=sa.func.now(),
        )

    inspector = inspect(bind)
    uniques = {
        uc["name"] for uc in inspector.get_unique_constraints("lead_info_extra")
    }
    if "uix_lead_info_extra_usuario_dominio" not in uniques:
        op.create_unique_constraint(
            "uix_lead_info_extra_usuario_dominio",
            "lead_info_extra",
            ["user_email_lower", "dominio"],
        )

    indexes = {ix["name"] for ix in inspector.get_indexes("lead_info_extra")}
    if "ix_lead_info_extra_user_email_lower" not in indexes:
        op.create_index(
            "ix_lead_info_extra_user_email_lower",
            "lead_info_extra",
            ["user_email_lower"],
        )
    if "ix_lead_info_extra_dominio" not in indexes:
        op.create_index(
            "ix_lead_info_extra_dominio",
            "lead_info_extra",
            ["dominio"],
        )


def _ensure_lead_estado(bind):
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "lead_estado" not in tables:
        op.create_table(
            "lead_estado",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_email_lower", sa.Text, nullable=False),
            sa.Column("dominio", sa.Text, nullable=False),
            sa.Column(
                "estado",
                sa.Text,
                nullable=False,
                server_default="pendiente",
            ),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "user_email_lower",
                "dominio",
                name="uix_lead_estado_usuario_dominio",
            ),
        )
        op.create_index(
            "ix_lead_estado_user_email_lower",
            "lead_estado",
            ["user_email_lower"],
        )
        op.create_index(
            "ix_lead_estado_dominio",
            "lead_estado",
            ["dominio"],
        )
        return

    with bind.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM lead_estado a
                USING lead_estado b
                WHERE a.ctid < b.ctid
                  AND a.user_email_lower IS NOT DISTINCT FROM b.user_email_lower
                  AND a.dominio IS NOT DISTINCT FROM b.dominio
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_estado
                   SET user_email_lower = CONCAT('__legacy_user__:', id)
                 WHERE user_email_lower IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_estado
                   SET dominio = CONCAT('__legacy_domain__:', id)
                 WHERE dominio IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_estado
                   SET estado = 'pendiente'
                 WHERE estado IS NULL OR estado = ''
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE lead_estado
                   SET timestamp = NOW()
                 WHERE timestamp IS NULL
                """
            )
        )

    inspector = inspect(bind)
    columns = {col["name"]: col for col in inspector.get_columns("lead_estado")}
    if "user_email_lower" not in columns:
        op.add_column(
            "lead_estado",
            sa.Column("user_email_lower", sa.Text, nullable=False, server_default=""),
        )
        op.execute(
            text(
                "UPDATE lead_estado SET user_email_lower = CONCAT('__legacy_user__:', id) WHERE user_email_lower = ''"
            )
        )
        op.alter_column(
            "lead_estado",
            "user_email_lower",
            existing_type=sa.Text(),
            nullable=False,
            server_default=None,
        )
    else:
        op.alter_column(
            "lead_estado",
            "user_email_lower",
            existing_type=columns["user_email_lower"]["type"],
            nullable=False,
        )

    if "dominio" not in columns:
        op.add_column(
            "lead_estado",
            sa.Column("dominio", sa.Text, nullable=False, server_default="__legacy_domain__"),
        )
        op.execute(
            text(
                "UPDATE lead_estado SET dominio = CONCAT('__legacy_domain__:', id) WHERE dominio = '__legacy_domain__'"
            )
        )
        op.alter_column(
            "lead_estado",
            "dominio",
            existing_type=sa.Text(),
            nullable=False,
            server_default=None,
        )
    else:
        op.alter_column(
            "lead_estado",
            "dominio",
            existing_type=columns["dominio"]["type"],
            nullable=False,
        )

    if "estado" not in columns:
        op.add_column(
            "lead_estado",
            sa.Column("estado", sa.Text, nullable=False, server_default="pendiente"),
        )
    else:
        op.alter_column(
            "lead_estado",
            "estado",
            existing_type=columns["estado"]["type"],
            nullable=False,
            server_default="pendiente",
        )

    if "timestamp" not in columns:
        op.add_column(
            "lead_estado",
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    else:
        op.alter_column(
            "lead_estado",
            "timestamp",
            existing_type=columns["timestamp"]["type"],
            nullable=False,
            server_default=sa.func.now(),
        )

    inspector = inspect(bind)
    uniques = {uc["name"] for uc in inspector.get_unique_constraints("lead_estado")}
    if "uix_lead_estado_usuario_dominio" not in uniques:
        op.create_unique_constraint(
            "uix_lead_estado_usuario_dominio",
            "lead_estado",
            ["user_email_lower", "dominio"],
        )

    indexes = {ix["name"] for ix in inspector.get_indexes("lead_estado")}
    if "ix_lead_estado_user_email_lower" not in indexes:
        op.create_index(
            "ix_lead_estado_user_email_lower",
            "lead_estado",
            ["user_email_lower"],
        )
    if "ix_lead_estado_dominio" not in indexes:
        op.create_index(
            "ix_lead_estado_dominio",
            "lead_estado",
            ["dominio"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_lead_info_extra(bind)
    _ensure_lead_estado(bind)


def downgrade() -> None:
    # Revert indexes and constraints created in upgrade.
    op.drop_index("ix_lead_estado_dominio", table_name="lead_estado")
    op.drop_index("ix_lead_estado_user_email_lower", table_name="lead_estado")
    with op.batch_alter_table("lead_estado") as batch:
        batch.drop_constraint("uix_lead_estado_usuario_dominio", type_="unique")

    op.drop_index("ix_lead_info_extra_dominio", table_name="lead_info_extra")
    op.drop_index(
        "ix_lead_info_extra_user_email_lower", table_name="lead_info_extra"
    )
    with op.batch_alter_table("lead_info_extra") as batch:
        batch.drop_constraint("uix_lead_info_extra_usuario_dominio", type_="unique")
