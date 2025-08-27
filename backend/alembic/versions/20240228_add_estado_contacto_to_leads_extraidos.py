from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240228_add_estado_contacto_to_leads_extraidos'
down_revision = '20250108_unify_tenant_key'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE leads_extraidos
        ADD COLUMN IF NOT EXISTS estado_contacto VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE leads_extraidos
        DROP COLUMN IF EXISTS estado_contacto
        """
    )
