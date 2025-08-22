from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250108_unify_tenant_key'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add user_email_lower to lead_nota
    op.add_column('lead_nota', sa.Column('user_email_lower', sa.String(length=255), nullable=True))
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
    op.create_index('ix_lead_nota_user_email_lower_url', 'lead_nota', ['user_email_lower', 'url'])

    # 5) Unique constraint on leads_extraidos (user_email_lower, url)
    op.create_unique_constraint(
        'uq_leads_extraidos_user_url', 'leads_extraidos', ['user_email_lower', 'url']
    )

    # 6) Composite index on lead_tarea for common lookups
    op.create_index(
        'ix_lead_tarea_user_dom_comp_prio_fecha_ts',
        'lead_tarea',
        ['user_email_lower', 'dominio', 'completado', 'prioridad', 'fecha', 'timestamp']
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
