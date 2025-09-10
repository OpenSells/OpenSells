"""add historial and lead_estado tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251115_add_historial_and_lead_estado'
down_revision = '20251010_leads_extraidos_unique_dominio'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if 'historial' not in tables:
        op.create_table(
            'historial',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_email', sa.String, nullable=False, index=True),
            sa.Column('filename', sa.String),
            sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    if 'lead_estado' not in tables:
        op.create_table(
            'lead_estado',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_email_lower', sa.String, nullable=False),
            sa.Column('url', sa.String),
            sa.Column('dominio', sa.String),
            sa.Column('estado', sa.String, nullable=False, server_default='pendiente'),
            sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('user_email_lower', 'dominio', name='uix_lead_estado_usuario_dominio'),
        )
        op.create_index('ix_lead_estado_user_email_lower', 'lead_estado', ['user_email_lower'])

def downgrade():
    op.drop_table('lead_estado')
    op.drop_table('historial')
