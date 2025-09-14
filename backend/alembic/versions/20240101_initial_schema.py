"""initial schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240101_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('user_email_lower', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('suspendido', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_index('ix_usuarios_email_lower', 'usuarios', ['user_email_lower'], unique=True)

    op.create_table(
        'leads_extraidos',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email_lower', sa.String(length=255), nullable=False),
        sa.Column('dominio', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text()),
        sa.Column('telefono', sa.String(length=50)),
        sa.Column('email', sa.String(length=255)),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_email_lower', 'dominio', name='uix_leads_usuario_dominio'),
    )
    op.create_index('ix_leads_extraidos_user_email_lower', 'leads_extraidos', ['user_email_lower'])

    op.create_table(
        'lead_tarea',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email_lower', sa.String(length=255), nullable=False),
        sa.Column('dominio', sa.String(length=255)),
        sa.Column('texto', sa.Text()),
        sa.Column('fecha', sa.DateTime()),
        sa.Column('completado', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('tipo', sa.String(length=50)),
        sa.Column('nicho', sa.String(length=255)),
        sa.Column('prioridad', sa.String(length=10)),
        sa.Column('auto', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_index('ix_lead_tarea_user_email_lower', 'lead_tarea', ['user_email_lower'])
    op.create_index(
        'ix_lead_tarea_user_dom_comp_prio_fecha_ts',
        'lead_tarea',
        ['user_email_lower', 'dominio', 'completado', 'prioridad', 'fecha', 'timestamp']
    )

    op.create_table(
        'lead_nota',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email_lower', sa.String(length=255), nullable=True),
        sa.Column('url', sa.Text()),
        sa.Column('nota', sa.Text()),
    )
    op.create_index('ix_lead_nota_user_email_lower_url', 'lead_nota', ['user_email_lower', 'url'])

    op.create_table(
        'lead_info_extra',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email_lower', sa.String(length=255), nullable=True),
        sa.Column('dominio', sa.String(length=255)),
        sa.Column('clave', sa.String(length=100)),
        sa.Column('valor', sa.Text()),
    )
    op.create_index('ix_lead_info_extra_user_email_lower', 'lead_info_extra', ['user_email_lower'])

    op.create_table(
        'historial',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email_lower', sa.String(length=255), nullable=True),
        sa.Column('mensaje', sa.Text()),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_historial_user_email_lower', 'historial', ['user_email_lower'])

    op.create_table(
        'lead_estado',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email_lower', sa.String(length=255), nullable=False),
        sa.Column('dominio', sa.String(length=255), nullable=False),
        sa.Column('estado', sa.String(length=50)),
        sa.UniqueConstraint('user_email_lower', 'dominio', name='uix_lead_estado_usuario_dominio'),
    )
    op.create_index('ix_lead_estado_user_email_lower', 'lead_estado', ['user_email_lower'])

    op.create_table(
        'usuario_memoria',
        sa.Column('user_email_lower', sa.String(length=255), primary_key=True),
        sa.Column('memoria', sa.Text()),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer),
        sa.Column('metric', sa.String(length=50)),
        sa.Column('period_key', sa.String(length=20)),
        sa.Column('valor', sa.Integer, server_default=sa.text('0')),
        sa.UniqueConstraint('user_id', 'metric', 'period_key', name='uix_usage_counter'),
    )
    op.create_index(
        'idx_usage_counters_user_metric_period',
        'usage_counters',
        ['user_id', 'metric', 'period_key']
    )

    op.create_table(
        'user_usage_monthly',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer),
        sa.Column('period_yyyymm', sa.String(length=6)),
        sa.Column('leads', sa.Integer, server_default=sa.text('0')),
        sa.Column('ia_msgs', sa.Integer, server_default=sa.text('0')),
        sa.Column('exports', sa.Integer, server_default=sa.text('0')),
        sa.UniqueConstraint('user_id', 'period_yyyymm', name='uix_user_usage_monthly'),
    )


def downgrade():
    op.drop_table('user_usage_monthly')
    op.drop_index('idx_usage_counters_user_metric_period', table_name='usage_counters')
    op.drop_table('usage_counters')
    op.drop_table('usuario_memoria')
    op.drop_index('ix_lead_estado_user_email_lower', table_name='lead_estado')
    op.drop_table('lead_estado')
    op.drop_index('ix_historial_user_email_lower', table_name='historial')
    op.drop_table('historial')
    op.drop_index('ix_lead_info_extra_user_email_lower', table_name='lead_info_extra')
    op.drop_table('lead_info_extra')
    op.drop_index('ix_lead_nota_user_email_lower_url', table_name='lead_nota')
    op.drop_table('lead_nota')
    op.drop_index('ix_lead_tarea_user_dom_comp_prio_fecha_ts', table_name='lead_tarea')
    op.drop_index('ix_lead_tarea_user_email_lower', table_name='lead_tarea')
    op.drop_table('lead_tarea')
    op.drop_index('ix_leads_extraidos_user_email_lower', table_name='leads_extraidos')
    op.drop_table('leads_extraidos')
    op.drop_index('ix_usuarios_email_lower', table_name='usuarios')
    op.drop_table('usuarios')
