import importlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import Usuario
from backend.auth import get_current_user
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import backend.models  # ensure models imported

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def make_user(plan: str) -> Usuario:
    u = Usuario(id=1, email="u@example.com", hashed_password="", plan=plan)
    u.email_lower = u.email
    return u


def test_export_csv_block_free():
    def override_user():
        return make_user("free")

    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)
    payload = {"urls": ["https://example.com"], "pais": "ES", "nicho": "test"}
    resp = client.post("/exportar_csv", json=payload)
    assert resp.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


def test_leads_quota_exceeded(monkeypatch):
    from backend.core import plans as plan_module

    monkeypatch.setattr(plan_module.PLANS["free"], "leads_por_mes", 1)

    def override_user():
        return make_user("free")

    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)
    monkeypatch.setattr("backend.main.extraer_datos_desde_url", lambda url, pais: {})
    client.post("/extraer_datos", json={"url": "https://a.com"})
    resp = client.post("/extraer_datos", json={"url": "https://b.com"})
    assert resp.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


def test_mi_plan_returns_limits():
    def override_user():
        return make_user("basico")

    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)
    resp = client.get("/mi_plan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "basico"
    assert data["limits"]["leads_por_mes"] == 200
    app.dependency_overrides.pop(get_current_user, None)
