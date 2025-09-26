"""ensure nicho column and indexes on lead_historial"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20250928_add_nicho_to_lead_historial"
down_revision = "20250926_add_lead_historial"
branch_labels = None
depends_on = None


_LEAD_HISTORIAL_TABLE = "lead_historial"
_IDX_USER_TIPO_NICHO = "idx_lead_historial_user_tipo_nicho"
_IDX_USER_TIPO_DOMINIO = "idx_lead_historial_user_tipo_dominio"


def _table_exists(inspector) -> bool:
    return _LEAD_HISTORIAL_TABLE in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector):
        return

    columns = {col["name"] for col in inspector.get_columns(_LEAD_HISTORIAL_TABLE)}
    if "nicho" not in columns:
        with op.batch_alter_table(_LEAD_HISTORIAL_TABLE) as batch_op:
            batch_op.add_column(sa.Column("nicho", sa.Text(), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_LEAD_HISTORIAL_TABLE)}

    if _IDX_USER_TIPO_NICHO not in existing_indexes:
        op.create_index(
            _IDX_USER_TIPO_NICHO,
            _LEAD_HISTORIAL_TABLE,
            ["user_email_lower", "tipo", "nicho"],
        )

    if _IDX_USER_TIPO_DOMINIO not in existing_indexes:
        op.create_index(
            _IDX_USER_TIPO_DOMINIO,
            _LEAD_HISTORIAL_TABLE,
            ["user_email_lower", "tipo", "dominio"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector):
        return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_LEAD_HISTORIAL_TABLE)}

    if _IDX_USER_TIPO_DOMINIO in existing_indexes:
        op.drop_index(_IDX_USER_TIPO_DOMINIO, table_name=_LEAD_HISTORIAL_TABLE)

    if _IDX_USER_TIPO_NICHO in existing_indexes:
        op.drop_index(_IDX_USER_TIPO_NICHO, table_name=_LEAD_HISTORIAL_TABLE)

    columns = {col["name"] for col in inspector.get_columns(_LEAD_HISTORIAL_TABLE)}
    if "nicho" in columns:
        with op.batch_alter_table(_LEAD_HISTORIAL_TABLE) as batch_op:
            batch_op.drop_column("nicho")
