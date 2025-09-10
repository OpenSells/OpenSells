import os
import subprocess
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app, get_db
from backend.database import Base
from backend.models import Usuario, LeadExtraido
from backend.auth import hashear_password


def test_no_legacy_tables_and_grep():
    from backend.models import Base as ModelsBase
    assert "users" not in ModelsBase.metadata.tables
    assert "usage_counters" not in ModelsBase.metadata.tables

    result = subprocess.run(
        ["rg", "--files-with-matches", r"\b(users|usage_counters)\b", "backend"],
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    allow = {"backend/alembic/versions/20250910_drop_legacy_users_usage_counters.py"}
    assert set(files).issubset(allow)


def test_endpoints_do_not_touch_legacy_tables(caplog):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    os.environ.setdefault("ALLOW_ANON_USER", "1")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
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
    caplog.set_level("INFO")
    client = TestClient(app)

    with TestingSessionLocal() as db:
        user = Usuario(email="tester@example.com", hashed_password=hashear_password("secret"))
        db.add(user)
        db.flush()
        lead = LeadExtraido(
            user_email=user.email,
            user_email_lower=user.email.lower(),
            dominio="example.com",
            url="example.com",
            nicho="n",
            nicho_original="n",
        )
        db.add(lead)
        db.commit()
        lead_id = lead.id

    resp = client.post("/login", json={"email": "tester@example.com", "password": "secret"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r2 = client.patch(
        f"/leads/{lead_id}/estado_contacto",
        json={"estado_contacto": "contactado"},
        headers=headers,
    )
    assert r2.status_code == 200

    r3 = client.get("/mi_plan", headers=headers)
    assert r3.status_code == 200

    assert "users" not in caplog.text
    assert "usage_counters" not in caplog.text

    app.dependency_overrides.clear()
