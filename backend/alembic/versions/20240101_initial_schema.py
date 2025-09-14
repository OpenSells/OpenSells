"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "20240101_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("plan", sa.String(), server_default="free"),
        sa.Column("suspendido", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_usuarios_email_lower",
        "usuarios",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.create_table(
        "lead_tarea",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("user_email_lower", sa.String(), nullable=False),
        sa.Column("dominio", sa.String()),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("fecha", sa.String()),
        sa.Column("completado", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("timestamp", sa.String()),
        sa.Column("tipo", sa.String(), server_default="lead"),
        sa.Column("nicho", sa.String()),
        sa.Column("prioridad", sa.String(), server_default="media"),
        sa.Column("auto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_lead_tarea_user_email_lower", "lead_tarea", ["user_email_lower"])

    op.create_table(
        "lead_historial",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("user_email_lower", sa.String(), nullable=False),
        sa.Column("dominio", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_lead_historial_user_email_lower", "lead_historial", ["user_email_lower"])

    op.create_table(
        "lead_nota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("user_email_lower", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("nota", sa.Text()),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_lead_nota_user_email_lower", "lead_nota", ["user_email_lower"])

    op.create_table(
        "lead_info_extra",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dominio", sa.String(), nullable=False),
        sa.Column("email", sa.String()),
        sa.Column("telefono", sa.String()),
        sa.Column("informacion", sa.Text()),
        sa.Column("user_email", sa.String()),
        sa.Column("user_email_lower", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_lead_info_extra_user_email_lower", "lead_info_extra", ["user_email_lower"])

    op.create_table(
        "leads_extraidos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("user_email_lower", sa.String(), nullable=False),
        sa.Column("dominio", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("nicho", sa.String(), nullable=False),
        sa.Column("nicho_original", sa.String(), nullable=False),
        sa.Column("estado_contacto", sa.String(20), nullable=False, server_default="pendiente"),
        sa.UniqueConstraint("user_email_lower", "dominio", name="uix_leads_usuario_dominio"),
    )
    op.create_index("ix_leads_extraidos_user_email_lower", "leads_extraidos", ["user_email_lower"])
    op.create_index("ix_leads_extraidos_estado_contacto", "leads_extraidos", ["estado_contacto"])

    op.create_table(
        "usuario_memoria",
        sa.Column("email_lower", sa.String(), primary_key=True),
        sa.Column("descripcion", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "historial",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("filename", sa.String()),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_historial_user_email", "historial", ["user_email"])

    op.create_table(
        "user_usage_monthly",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("period_yyyymm", sa.String(), nullable=False, index=True),
        sa.Column("leads", sa.Integer(), server_default="0"),
        sa.Column("ia_msgs", sa.Integer(), server_default="0"),
        sa.Column("tasks", sa.Integer(), server_default="0"),
        sa.Column("csv_exports", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "period_yyyymm", name="uix_user_usage_monthly"),
    )
    op.create_index(
        "idx_uum_user_period",
        "user_usage_monthly",
        ["user_id", "period_yyyymm"],
    )

    op.create_table(
        "lead_estado",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_email_lower", sa.String(), nullable=False),
        sa.Column("url", sa.String()),
        sa.Column("dominio", sa.String()),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_email_lower", "dominio", name="uix_lead_estado_usuario_dominio"),
    )
    op.create_index("ix_lead_estado_user_email_lower", "lead_estado", ["user_email_lower"])


def downgrade() -> None:
    op.drop_index("ix_lead_estado_user_email_lower", table_name="lead_estado")
    op.drop_table("lead_estado")
    op.drop_index("ix_historial_user_email", table_name="historial")
    op.drop_table("historial")
    op.drop_index("idx_uum_user_period", table_name="user_usage_monthly")
    op.drop_table("user_usage_monthly")
    op.drop_table("usuario_memoria")
    op.drop_index("ix_leads_extraidos_estado_contacto", table_name="leads_extraidos")
    op.drop_index("ix_leads_extraidos_user_email_lower", table_name="leads_extraidos")
    op.drop_table("leads_extraidos")
    op.drop_index("ix_lead_info_extra_user_email_lower", table_name="lead_info_extra")
    op.drop_table("lead_info_extra")
    op.drop_index("ix_lead_nota_user_email_lower", table_name="lead_nota")
    op.drop_table("lead_nota")
    op.drop_index("ix_lead_historial_user_email_lower", table_name="lead_historial")
    op.drop_table("lead_historial")
    op.drop_index("ix_lead_tarea_user_email_lower", table_name="lead_tarea")
    op.drop_table("lead_tarea")
    op.drop_index("ix_usuarios_email_lower", table_name="usuarios")
    op.drop_table("usuarios")
