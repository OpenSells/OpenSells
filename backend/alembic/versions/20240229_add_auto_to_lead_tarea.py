from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240229_add_auto_to_lead_tarea'
down_revision = '20240228_add_estado_contacto_to_leads_extraidos'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    exists = conn.execute(sa.text(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'lead_tarea' AND column_name = 'auto'
        """
    )).scalar()
    if not exists:
        op.add_column(
            'lead_tarea',
            sa.Column('auto', sa.Boolean(), server_default=sa.text('false'), nullable=False)
        )


def downgrade():
    conn = op.get_bind()
    exists = conn.execute(sa.text(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'lead_tarea' AND column_name = 'auto'
        """
    )).scalar()
    if exists:
        op.drop_column('lead_tarea', 'auto')
