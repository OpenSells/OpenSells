import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import get_db
from backend.auth import get_current_user
from backend.models import Base, LeadTarea


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


def test_crear_tarea(client_session):
    client, session = client_session
    payload = {
        "texto": "llamar",
        "fecha": "2024-01-01",
        "prioridad": "alta",
        "tipo": "lead",
        "dominio": "example.com",
        "nicho": "peluquerias",
        "auto": False,
    }
    r = client.post("/tareas", json=payload)
    assert r.status_code in (200, 201)
    tarea = session.query(LeadTarea).first()
    assert tarea is not None
    assert tarea.completado is False
    assert tarea.auto is False
    assert tarea.user_email_lower == "test@example.com"
