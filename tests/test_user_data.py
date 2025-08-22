import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from backend.main import app
from backend.database import Base, engine, SessionLocal, bootstrap_database
from datetime import datetime, timedelta
from backend.models import Usuario, Nicho, LeadExtraido, LeadTarea, Suscripcion
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
            dominio="a.com",
            nicho="marketing",
            nicho_original="Marketing",
        )
        lead2 = LeadExtraido(
            user_email=user.email_lower,
            user_email_lower=user.email_lower,
            url="https://b.com",
            dominio="b.com",
            nicho="marketing",
            nicho_original="Marketing",
        )
        tarea = LeadTarea(
            email=user.email_lower,
            user_email_lower=user.email_lower,
            texto="demo",
            tipo="general",
        )
        sus = Suscripcion(
            user_email_lower=user.email_lower,
            status="active",
            current_period_end=datetime.utcnow() + timedelta(days=1),
        )
        db.add_all([nicho, lead1, lead2, tarea, sus])
        db.commit()


@pytest.fixture()
def token(client):
    _seed_data()
    resp = client.post(
        "/login", data={"username": "test@example.com", "password": "pw"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_login_creates_user_with_free_plan(client):
    resp = client.post(
        "/login", data={"username": "nuevo@example.com", "password": "pw"}
    )
    assert resp.status_code == 200
    assert resp.json()["plan"] == "free"
    with SessionLocal() as db:
        user = db.query(Usuario).filter_by(email_lower="nuevo@example.com").first()
        assert user is not None
        assert user.plan == "free"


def test_mis_nichos(client, token):
    resp = client.get("/mis_nichos", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["nichos"][0]["total_leads"] == 2


def test_mis_leads(client, token):
    resp = client.get("/mis_leads", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    emails = {lead["user_email_lower"] for lead in data["leads"]}
    assert emails == {"test@example.com"}


def test_requires_auth(client):
    os.environ["ALLOW_ANON_USER"] = "0"
    try:
        assert client.get("/mis_nichos").status_code == 401
        assert client.get("/mis_leads").status_code == 401
    finally:
        os.environ["ALLOW_ANON_USER"] = "1"


def test_leads_por_nicho(client, token):
    resp = client.get(
        "/leads_por_nicho",
        params={"nicho": "marketing"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["leads"]) == 2


def test_tareas_pendientes(client, token):
    resp = client.get(
        "/tareas_pendientes", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert len(resp.json()["tareas"]) >= 1


def test_me_includes_plan(client, token):
    resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["plan_resuelto"] == "pro"
    assert data["email"] == "test@example.com"


def test_debug_user_snapshot(client, token):
    resp = client.get(
        "/debug-user-snapshot", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["leads_count"] == 2
    assert data["nichos_count"] == 1
    assert data["plan_resuelto"] == "pro"
    assert data["db_vendor"]
    inc = data.get("inconsistencias", {})
    assert inc.get("nichos_sin_user_email_lower") == 0
    assert inc.get("leads_sin_user_email_lower") == 0
    assert inc.get("leads_sin_nicho") == 0
    assert inc.get("leads_sin_dominio") == 0


def test_mi_plan_active_subscription(client):
    with SessionLocal() as db:
        user = Usuario(email="pro@example.com", hashed_password=hashear_password("pw"), plan="pro")
        db.add(user)
        db.commit()
        db.refresh(user)
        sus = Suscripcion(
            user_email_lower=user.email_lower,
            status="active",
            current_period_end=datetime.utcnow() + timedelta(days=1),
        )
        db.add(sus)
        db.commit()
    resp = client.post(
        "/login", data={"username": "pro@example.com", "password": "pw"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    resp = client.get("/mi_plan", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["plan_resuelto"] == "pro"


def test_guard_requires_subscription(client):
    with SessionLocal() as db:
        user = Usuario(email="nosub@example.com", hashed_password=hashear_password("pw"))
        db.add(user)
        db.commit()
    resp = client.post("/login", data={"username": "nosub@example.com", "password": "pw"})
    token = resp.json()["access_token"]
    r = client.get("/tareas_pendientes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_plan_change_without_new_token(client):
    with SessionLocal() as db:
        user = Usuario(email="flip@example.com", hashed_password=hashear_password("pw"))
        db.add(user)
        db.commit()
    resp = client.post("/login", data={"username": "flip@example.com", "password": "pw"})
    token = resp.json()["access_token"]
    # initially should be 403
    assert client.get("/tareas_pendientes", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    # activate subscription without regenerating token
    with SessionLocal() as db:
        sus = Suscripcion(
            user_email_lower="flip@example.com",
            status="active",
            current_period_end=datetime.utcnow() + timedelta(days=1),
        )
        db.add(sus)
        db.commit()
    assert client.get("/tareas_pendientes", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_bootstrap_backfills_legacy_leads(client):
    # Insert legacy lead missing dominio and user_email_lower
    with SessionLocal() as db:
        user = Usuario(email="legacy@example.com", hashed_password=hashear_password("pw"))
        db.add(user)
        db.commit()
        db.refresh(user)
    # Insert legacy row via raw SQL to skip validators
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO leads_extraidos (user_email, user_email_lower, url, dominio, nicho, nicho_original) "
                "VALUES (:ue, '', :url, '', 'legacy', 'Legacy')"
            ),
            {"ue": "legacy@example.com", "url": "https://legacy.com/page"},
        )
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT dominio FROM leads_extraidos WHERE url=:u"
            ),
            {"u": "https://legacy.com/page"},
        ).fetchone()
        assert row and row.dominio == ""

    # Run bootstrap to backfill
    bootstrap_database()
    bootstrap_database()  # idempotent second run

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT dominio, user_email_lower FROM leads_extraidos WHERE url=:u"
            ),
            {"u": "https://legacy.com/page"},
        ).fetchone()
    assert row is not None
    assert row.dominio == "legacy.com"
    assert row.user_email_lower == "legacy@example.com"

    with engine.begin() as conn:
        inspector = inspect(conn)
        ucs = {uc["name"] for uc in inspector.get_unique_constraints("leads_extraidos")}
        assert "uq_user_dominio" in ucs
