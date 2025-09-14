from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250108_unify_tenant_key'
down_revision = '20240101_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # 1) Add user_email_lower to lead_nota if missing
    conn.execute(
        sa.text(
            "ALTER TABLE lead_nota ADD COLUMN IF NOT EXISTS user_email_lower VARCHAR(255)"
        )
    )
    # 2) Backfill from leads_extraidos based on url and user
    op.execute(
        """
        UPDATE lead_nota ln
        SET user_email_lower = le.user_email_lower
        FROM leads_extraidos le
        WHERE ln.url = le.url
          AND ln.user_email_lower IS NULL
        """
    )
    # 3) Drop legacy email_lower column if exists
    with op.batch_alter_table('lead_nota') as batch_op:
        try:
            batch_op.drop_index('ix_lead_nota_email_lower')
        except Exception:
            pass
        try:
            batch_op.drop_column('email_lower')
        except Exception:
            pass
    # 4) Enforce NOT NULL and index
    op.alter_column('lead_nota', 'user_email_lower', existing_type=sa.String(length=255), nullable=False)
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'ix_lead_nota_user_email_lower_url'
                      AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX ix_lead_nota_user_email_lower_url ON lead_nota (user_email_lower, url);
                END IF;
            END$$;
            """
        )
    )

    # 5) Unique constraint on leads_extraidos (user_email_lower, url)
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
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

    # 6) Composite index on lead_tarea for common lookups
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_lead_tarea_user_dom_comp_prio_fecha_ts
            ON lead_tarea (user_email_lower, dominio, completado, prioridad, fecha, timestamp)
            """
        )
    )


def downgrade():
    # Drop composite index from lead_tarea
    op.drop_index('ix_lead_tarea_user_dom_comp_prio_fecha_ts', table_name='lead_tarea')
    # Drop unique constraint from leads_extraidos
    op.drop_constraint('uq_leads_extraidos_user_url', 'leads_extraidos', type_='unique')
    # Drop index and column from lead_nota
    op.drop_index('ix_lead_nota_user_email_lower_url', table_name='lead_nota')
    op.drop_column('lead_nota', 'user_email_lower')
    # Restore legacy column for completeness
    op.add_column('lead_nota', sa.Column('email_lower', sa.String(length=255), nullable=True))
    op.create_index('ix_lead_nota_email_lower', 'lead_nota', ['email_lower'])
