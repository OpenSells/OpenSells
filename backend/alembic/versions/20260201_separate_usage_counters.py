from alembic import op
import sqlalchemy as sa

revision = '20260201_separate_usage_counters'
down_revision = '20260101_add_user_usage_monthly'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS usage_counters")
    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_month', sa.Date(), nullable=False),
        sa.Column('leads_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('searches_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'period_month', name='uix_usage_user_period')
    )
    op.create_index('idx_usage_user_period', 'usage_counters', ['user_id', 'period_month'])


def downgrade():
    op.drop_index('idx_usage_user_period', table_name='usage_counters')
    op.drop_table('usage_counters')
