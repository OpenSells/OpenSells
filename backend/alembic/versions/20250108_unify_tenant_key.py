from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250108_unify_tenant_key"
down_revision = "20240101_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1) lead_nota: añadir columna si no existe
    op.execute(
        sa.text(
            "ALTER TABLE lead_nota "
            "ADD COLUMN IF NOT EXISTS user_email_lower VARCHAR(255)"
        )
    )

    # 2) Rellenar user_email_lower a partir de leads_extraidos usando la URL
    op.execute(
        sa.text(
            """
            UPDATE lead_nota ln
            SET user_email_lower = le.user_email_lower
            FROM leads_extraidos le
            WHERE ln.url = le.url
              AND ln.user_email_lower IS NULL
            """
        )
    )

    # 3) Limpieza de legado en lead_nota (sin fallar si no existe)
    #    - borrar índice viejo si existe
    op.execute("DROP INDEX IF EXISTS ix_lead_nota_email_lower")
    #    - borrar columna vieja si existe
    op.execute("ALTER TABLE lead_nota DROP COLUMN IF EXISTS email_lower")

    # 4) Enforce NOT NULL y crear índice compuesto (idempotente)
    #    (Si quedaran NULL residuales en una BD vieja, esta línea fallaría;
    #     en instalaciones nuevas no habrá filas. Ajustar si fuese necesario.)
    op.execute(
        sa.text(
            "ALTER TABLE lead_nota "
            "ALTER COLUMN user_email_lower SET NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_lead_nota_user_email_lower_url "
            "ON lead_nota (user_email_lower, url)"
        )
    )

    # 5) Constraint única en leads_extraidos (user_email_lower, url) si no existe
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_leads_extraidos_user_url'
                      AND conrelid = 'leads_extraidos'::regclass
                ) THEN
                    ALTER TABLE leads_extraidos
                    ADD CONSTRAINT uq_leads_extraidos_user_url
                    UNIQUE (user_email_lower, url);
                END IF;
            END$$;
            """
        )
    )

    # 6) Índice compuesto en lead_tarea para consultas comunes (idempotente)
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_lead_tarea_user_dom_comp_prio_fecha_ts
            ON lead_tarea (user_email_lower, dominio, completado, prioridad, fecha, "timestamp")
            """
        )
    )


def downgrade():
    # 1) lead_tarea: borrar índice si existe
    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS ix_lead_tarea_user_dom_comp_prio_fecha_ts"
        )
    )

    # 2) leads_extraidos: eliminar constraint única si existe
    op.execute(
        sa.text(
            "ALTER TABLE leads_extraidos "
            "DROP CONSTRAINT IF EXISTS uq_leads_extraidos_user_url"
        )
    )

    # 3) lead_nota: borrar índice compuesto y columna nueva si existen
    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS ix_lead_nota_user_email_lower_url"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE lead_nota DROP COLUMN IF EXISTS user_email_lower"
        )
    )

    # 4) Restaurar columna/índice legado (solo para coherencia del downgrade)
    op.execute(
        sa.text(
            "ALTER TABLE lead_nota "
            "ADD COLUMN IF NOT EXISTS email_lower VARCHAR(255)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_lead_nota_email_lower "
            "ON lead_nota (email_lower)"
        )
    )
