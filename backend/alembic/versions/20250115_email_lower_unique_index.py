"""ensure case-insensitive email index and drop redundant ones

Revision ID: 20250115_email_lower_unique_index
Revises: 20250108_unify_tenant_key
Create Date: 2025-01-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20250115_email_lower_unique_index"
down_revision = "20240229_add_auto_to_lead_tarea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create unique index on lower(email)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname='public' AND tablename='usuarios' AND indexname='ix_usuarios_email_lower'
            ) THEN
                CREATE UNIQUE INDEX ix_usuarios_email_lower ON public.usuarios (lower(email));
            END IF;
        END$$;
        """
    )

    # Drop redundant indices if present
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname='public' AND tablename='usuarios' AND indexname='ix_usuarios_id'
            ) THEN
                DROP INDEX public.ix_usuarios_id;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname='public' AND tablename='usuarios' AND indexname='ix_usuarios_email'
            ) THEN
                DROP INDEX public.ix_usuarios_email;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_usuarios_email_lower")
    # redundant indices are intentionally not recreated
