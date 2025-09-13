"""
Create user_usage_monthly table
"""

from alembic import op
import sqlalchemy as sa

revision = '20251201_create_user_usage_monthly'
down_revision = '20251115_add_historial_and_lead_estado'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_usage_monthly',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_email_lower', sa.String(), nullable=False),
        sa.Column('period_yyyymm', sa.String(), nullable=False),
        sa.Column('leads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ia_msgs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('csv_exports', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('searches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_email_lower', 'period_yyyymm', name='uix_user_period')
    )
    op.create_index('ix_user_usage_monthly_email', 'user_usage_monthly', ['user_email_lower'])


def downgrade():
    op.drop_index('ix_user_usage_monthly_email', table_name='user_usage_monthly')
    op.drop_table('user_usage_monthly')
