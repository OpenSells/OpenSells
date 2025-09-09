import importlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import pytest
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


def make_user(id: int, plan: str) -> Usuario:
    u = Usuario(id=id, email=f"u{id}@example.com", hashed_password="", plan=plan)
    u.email_lower = u.email
    return u


@pytest.fixture
def user_free():
    return make_user(1, "free")


@pytest.fixture
def user_basico():
    return make_user(2, "basico")


@pytest.fixture
def user_premium():
    return make_user(3, "premium")


def test_export_csv_block_free(user_free):
    app.dependency_overrides[get_current_user] = lambda: user_free
    client = TestClient(app)
    payload = {"urls": ["https://example.com"], "pais": "ES", "nicho": "test"}
    resp = client.post("/exportar_csv", json=payload)
    assert resp.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


def test_export_csv_allowed_basico(user_basico, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: user_basico
    monkeypatch.setattr("backend.db.obtener_todos_los_dominios_usuario", lambda *a, **k: [])
    monkeypatch.setattr("backend.db.guardar_leads_extraidos", lambda *a, **k: None)
    client = TestClient(app)
    payload = {"urls": ["https://example.com"], "pais": "ES", "nicho": "test"}
    resp = client.post("/exportar_csv", json=payload)
    assert resp.status_code == 200
    app.dependency_overrides.pop(get_current_user, None)


def test_leads_quota_exceeded(monkeypatch, user_free):
    from backend.core import plans as plan_module

    monkeypatch.setattr(plan_module.PLANS["free"], "leads_por_mes", 1)

    app.dependency_overrides[get_current_user] = lambda: user_free
    client = TestClient(app)
    monkeypatch.setattr("backend.main.extraer_datos_desde_url", lambda url, pais: {})
    client.post("/extraer_datos", json={"url": "https://a.com"})
    resp = client.post("/extraer_datos", json={"url": "https://b.com"})
    assert resp.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


def test_mi_plan_returns_limits(user_basico):
    app.dependency_overrides[get_current_user] = lambda: user_basico
    client = TestClient(app)
    resp = client.get("/mi_plan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "basico"
    assert data["limits"]["leads_por_mes"] == 200
    app.dependency_overrides.pop(get_current_user, None)


def test_premium_unlimited_messages(user_premium, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: user_premium

    class DummyResp:
        def __init__(self):
            self.choices = [type("obj", (), {"message": type("m", (), {"content": "OK"})()})()]

    class DummyClient:
        chat = type("obj", (), {"completions": type("obj", (), {"create": lambda *a, **k: DummyResp()})()})()

    monkeypatch.setattr("backend.main.openai_client", DummyClient())
    monkeypatch.setattr("backend.main.obtener_memoria_usuario_pg", lambda email: "")

    client = TestClient(app)
    payload = {"cliente_ideal": "foo"}
    client.post("/buscar", json=payload)
    resp = client.post("/buscar", json=payload)
    assert resp.status_code == 200
    app.dependency_overrides.pop(get_current_user, None)


def test_webhook_price_mapping(monkeypatch):
    import asyncio
    from backend import webhook as webhook_module

    monkeypatch.setattr(webhook_module, "PRICE_TO_PLAN", {"price_basico": "basico"})

    db = TestingSessionLocal()
    usuario = Usuario(email="hook@example.com", hashed_password="", plan="free")
    usuario.email_lower = usuario.email
    db.add(usuario)
    db.commit()

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_email": "hook@example.com",
                "lines": {"data": [{"price": {"id": "price_basico"}}]},
            }
        },
    }

    async def call(p):
        class DummyRequest:
            async def json(self_inner):
                return p

        await webhook_module.stripe_webhook(DummyRequest(), db)

    asyncio.run(call(payload))
    assert db.query(Usuario).filter_by(email="hook@example.com").first().plan == "basico"

    payload["data"]["object"]["lines"]["data"][0]["price"]["id"] = "price_unknown"
    asyncio.run(call(payload))
    assert db.query(Usuario).filter_by(email="hook@example.com").first().plan == "free"

    db.close()
