import pytest
import sqlalchemy as sa
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from backend.models import Base, Usuario, LeadExtraido


def create_session():
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def test_indexes_and_constraints_exist():
    engine, session = create_session()
    insp = sa.inspect(engine)

    result = session.execute(sa.text("PRAGMA index_list('usuarios')")).fetchall()
    idx_names = {row[1]: row[2] for row in result}  # name -> unique flag
    assert idx_names.get("ix_usuarios_email_lower") == 1
    assert "ix_usuarios_id" not in idx_names

    lead_constraints = insp.get_unique_constraints("leads_extraidos")
    assert any(c["name"] == "uix_leads_usuario_dominio" for c in lead_constraints)


def test_unique_enforcement():
    engine, session = create_session()

    session.add(Usuario(email="Email@dom.com", hashed_password="x"))
    session.commit()
    session.add(Usuario(email="email@dom.com", hashed_password="y"))
    with pytest.raises(Exception):
        session.commit()
    session.rollback()

    lead = LeadExtraido(
        user_email="a",
        user_email_lower="a",
        dominio="example.com",
        url="example.com",
        nicho="n",
        nicho_original="n",
    )
    session.add(lead)
    session.commit()
    session.add(
        LeadExtraido(
            user_email="a",
            user_email_lower="a",
            dominio="example.com",
            url="example.com",
            nicho="n",
            nicho_original="n",
        )
    )
    with pytest.raises(Exception):
        session.commit()
