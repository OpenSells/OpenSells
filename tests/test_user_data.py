import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models import Usuario, Nicho, LeadExtraido, LeadTarea
from backend.auth import hashear_password


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _seed_data():
    with SessionLocal() as db:
        user = Usuario(email="test@example.com", hashed_password=hashear_password("pw"))
        db.add(user)
        db.commit()
        db.refresh(user)
        nicho = Nicho(
            user_email_lower=user.email_lower,
            nicho="marketing",
            nicho_original="Marketing",
        )
        lead1 = LeadExtraido(
            user_email=user.email_lower,
            user_email_lower=user.email_lower,
            url="https://a.com",
            nicho="marketing",
            nicho_original="Marketing",
        )
        lead2 = LeadExtraido(
            user_email=user.email_lower,
            user_email_lower=user.email_lower,
            url="https://b.com",
            nicho="marketing",
            nicho_original="Marketing",
        )
        tarea = LeadTarea(
            email=user.email_lower,
            user_email_lower=user.email_lower,
            texto="demo",
            tipo="general",
        )
        db.add_all([nicho, lead1, lead2, tarea])
        db.commit()


@pytest.fixture()
def token(client):
    _seed_data()
    resp = client.post(
        "/login", data={"username": "test@example.com", "password": "pw"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_mis_nichos(client, token):
    resp = client.get("/mis_nichos", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["nichos"][0]["total_leads"] == 2


def test_tareas_pendientes(client, token):
    resp = client.get(
        "/tareas_pendientes", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert len(resp.json()["tareas"]) >= 1


def test_debug_user_snapshot(client, token):
    resp = client.get(
        "/debug-user-snapshot", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["leads"] == 2
    assert data["plan"] == "free"
