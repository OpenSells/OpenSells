from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
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

    def override_get_current_user():
        return SimpleNamespace(email_lower="test@example.com")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client, session
    session.close()
    app.dependency_overrides.clear()


def seed(session, user_email_lower: str):
    datos = [
        {"tipo": "general", "completado": False, "texto": "G1"},
        {"tipo": "general", "completado": True, "texto": "G2"},
        {"tipo": "nicho", "completado": False, "texto": "N1", "nicho": "peluquerias"},
        {"tipo": "lead", "completado": False, "texto": "L1", "dominio": "example.com"},
    ]
    for d in datos:
        session.add(
            LeadTarea(
                email=user_email_lower,
                user_email_lower=user_email_lower,
                dominio=d.get("dominio"),
                texto=d["texto"],
                fecha=None,
                completado=d["completado"],
                timestamp="1",
                tipo=d["tipo"],
                nicho=d.get("nicho"),
                prioridad=2,
            )
        )
    session.commit()


def test_filtro_general_pendientes(client_session):
    client, session = client_session
    seed(session, "test@example.com")
    r = client.get("/tareas_pendientes?tipo=general&solo_pendientes=true")
    assert r.status_code == 200
    textos = [t["texto"] for t in r.json()]
    assert "G1" in textos and "G2" not in textos


def test_filtro_nicho(client_session):
    client, session = client_session
    seed(session, "test@example.com")
    r = client.get("/tareas_pendientes?tipo=nicho&solo_pendientes=true")
    assert r.status_code == 200
    textos = [t["texto"] for t in r.json()]
    assert textos == ["N1"]


def test_todas_incluye_completadas(client_session):
    client, session = client_session
    seed(session, "test@example.com")
    r = client.get("/tareas_pendientes?tipo=todas&solo_pendientes=false")
    assert r.status_code == 200
    textos = [t["texto"] for t in r.json()]
    assert set(textos) == {"G1", "G2", "N1", "L1"}
