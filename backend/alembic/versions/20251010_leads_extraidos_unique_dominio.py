"""enforce unique (user_email_lower, dominio) in leads_extraidos

Revision ID: 20251010_leads_extraidos_unique_dominio
Revises: 20250910_drop_legacy_users_usage_counters
Create Date: 2025-10-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "20251010_leads_extraidos_unique_dominio"
down_revision = "20250910_drop_legacy_users_usage_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Eliminar duplicados manteniendo el más reciente por (user_email_lower, dominio)
    #    Usamos la columna real 'creado_en' en lugar de 'timestamp'
    conn.execute(text("""
        DELETE FROM public.leads_extraidos t
        USING (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                         PARTITION BY user_email_lower, dominio
                         ORDER BY COALESCE(creado_en, NOW()) DESC, id DESC
                       ) AS rn
                FROM public.leads_extraidos
            ) z
            WHERE z.rn > 1
        ) d
        WHERE t.id = d.id;
    """))

    # 2) Si existe la constraint antigua por (user_email_lower, url), elimínala
    has_old = conn.execute(text("""
        SELECT 1
        FROM pg_constraint c
        WHERE c.conname = 'uq_leads_extraidos_user_url'
          AND c.conrelid = 'public.leads_extraidos'::regclass
        LIMIT 1;
    """)).scalar()
    if has_old:
        conn.execute(text("""
            ALTER TABLE public.leads_extraidos
            DROP CONSTRAINT uq_leads_extraidos_user_url;
        """))

    # 3) Crear UNIQUE (user_email_lower, dominio) sólo si no existe
    has_new = conn.execute(text("""
        SELECT 1
        FROM pg_constraint c
        WHERE c.conname = 'uix_leads_usuario_dominio'
          AND c.conrelid = 'public.leads_extraidos'::regclass
        LIMIT 1;
    """)).scalar()
    if not has_new:
        op.create_unique_constraint(
            'uix_leads_usuario_dominio',
            'leads_extraidos',
            ['user_email_lower', 'dominio']
        )


def downgrade() -> None:
    # Quita la UNIQUE si existe (idempotente en downgrade)
    op.execute("""
        ALTER TABLE public.leads_extraidos
        DROP CONSTRAINT IF EXISTS uix_leads_usuario_dominio;
    """)
