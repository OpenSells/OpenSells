import os
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

from backend.models import Base, LeadExtraido, LeadNota, LeadTarea
from backend.db import buscar_leads_global_postgres, obtener_todas_tareas_pendientes_postgres
from backend.main import app
from backend.database import get_db
from backend.auth import get_current_user


import pytest


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def seed_leads_and_notes(session):
    u1 = "u1@example.com"
    u2 = "u2@example.com"
    session.add_all([
        LeadExtraido(user_email=u1, user_email_lower=u1, url="example.com", nicho="n", nicho_original="n"),
        LeadExtraido(user_email=u2, user_email_lower=u2, url="example.com", nicho="n", nicho_original="n"),
        LeadNota(email=u1, user_email_lower=u1, url="example.com", nota="alpha"),
        LeadNota(email=u2, user_email_lower=u2, url="example.com", nota="beta"),
    ])
    session.commit()
    return u1, u2


def seed_tasks(session):
    u1 = "a@example.com"
    u2 = "b@example.com"
    session.add_all([
        LeadExtraido(user_email=u1, user_email_lower=u1, url="foo.com", nicho="n", nicho_original="n"),
        LeadExtraido(user_email=u2, user_email_lower=u2, url="foo.com", nicho="n", nicho_original="n"),
        LeadTarea(email=u1, user_email_lower=u1, dominio="foo.com", texto="t1", completado=False, fecha=None, timestamp="1"),
        LeadTarea(email=u2, user_email_lower=u2, dominio="foo.com", texto="t2", completado=False, fecha=None, timestamp="1"),
    ])
    session.commit()
    return u1, u2


def test_buscar_leads_filtrado_por_usuario(db_session):
    u1, u2 = seed_leads_and_notes(db_session)
    res1 = buscar_leads_global_postgres(u1, "alpha", db_session)
    res2 = buscar_leads_global_postgres(u2, "alpha", db_session)
    assert res1 == ["example.com"]
    assert res2 == []


def test_tareas_pendientes_join(db_session):
    u1, u2 = seed_tasks(db_session)
    tareas_u1 = obtener_todas_tareas_pendientes_postgres(u1, db_session)
    assert len(tareas_u1) == 1
    assert tareas_u1[0]["lead_url"] == "foo.com"


def test_conteo_leads_endpoint(db_session):
    user = "cnt@example.com"
    session = db_session
    session.add_all([
        LeadExtraido(user_email=user, user_email_lower=user, url="a.com", nicho="n", nicho_original="n"),
        LeadExtraido(user_email=user, user_email_lower=user, url="a.com", nicho="n", nicho_original="n"),
        LeadExtraido(user_email=user, user_email_lower=user, url="b.com", nicho="n", nicho_original="n"),
    ])
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    def override_get_current_user():
        return SimpleNamespace(email_lower=user)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    resp = client.get("/conteo_leads")
    assert resp.status_code == 200
    assert resp.json()["total_leads_distintos"] == 2

    app.dependency_overrides.clear()
