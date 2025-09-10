"""enforce unique (user_email_lower, dominio) in leads_extraidos

Revision ID: 20251010_leads_extraidos_unique_dominio
Revises: 20250910_drop_legacy_users_usage_counters
Create Date: 2025-10-10
"""

from alembic import op
import sqlalchemy as sa

revision = "20251010_leads_extraidos_unique_dominio"
down_revision = "20250910_drop_legacy_users_usage_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Remove duplicate (user_email_lower, dominio) keeping most recent
    bind.execute(
        sa.text(
            """
            DELETE FROM public.leads_extraidos t
            USING (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                             PARTITION BY user_email_lower, dominio
                             ORDER BY timestamp DESC, id DESC
                           ) AS rn
                    FROM public.leads_extraidos
                ) z
                WHERE z.rn > 1
            ) d
            WHERE t.id = d.id;
            """
        )
    )

    # Add unique constraint if not exists
    bind.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname='uq_leads_extraidos_user_url'
                      AND conrelid='leads_extraidos'::regclass
                ) THEN
                    ALTER TABLE public.leads_extraidos
                    DROP CONSTRAINT uq_leads_extraidos_user_url;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname='uix_leads_usuario_dominio'
                      AND conrelid='leads_extraidos'::regclass
                ) THEN
                    ALTER TABLE public.leads_extraidos
                    ADD CONSTRAINT uix_leads_usuario_dominio
                    UNIQUE (user_email_lower, dominio);
                END IF;
            END$$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.leads_extraidos DROP CONSTRAINT IF EXISTS uix_leads_usuario_dominio;"
    )
