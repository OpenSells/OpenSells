"""
Create usage_counters table
"""

from alembic import op
import sqlalchemy as sa

revision = '20251201_create_usage_counters'
down_revision = '20251115_add_historial_and_lead_estado'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('metric', sa.String(), nullable=False),
        sa.Column('period_key', sa.String(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('user_id', 'metric', 'period_key', name='uix_usage_counter')
    )


def downgrade():
    op.drop_table('usage_counters')
