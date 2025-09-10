import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.main import app
from backend.database import get_db
from backend.auth import get_current_user
from backend.models import Base, LeadExtraido


@pytest.fixture()
def client_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    def override_user():
        return SimpleNamespace(email_lower="test@example.com")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    client = TestClient(app)
    yield client, session

    session.close()
    app.dependency_overrides.clear()


def test_actualizar_estado_permitidos(client_session):
    client, session = client_session
    lead = LeadExtraido(
        user_email="test@example.com",
        user_email_lower="test@example.com",
        dominio="example.com",
        url="example.com",
        nicho="n",
        nicho_original="N",
    )
    session.add(lead)
    session.commit()

    for estado in ["pendiente", "contactado", "cerrado", "fallido"]:
        r = client.patch(f"/leads/{lead.id}/estado_contacto", json={"estado_contacto": estado})
        assert r.status_code == 200
        session.refresh(lead)
        assert lead.estado_contacto == estado


def test_actualizar_estado_invalido(client_session):
    client, session = client_session
    lead = LeadExtraido(
        user_email="test@example.com",
        user_email_lower="test@example.com",
        dominio="example.com",
        url="example.com",
        nicho="n",
        nicho_original="N",
    )
    session.add(lead)
    session.commit()

    r = client.patch(f"/leads/{lead.id}/estado_contacto", json={"estado_contacto": "otro"})
    assert r.status_code >= 400
