import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError

from backend.main import app, get_db
from backend.database import Base
from backend.models import Usuario
from backend.auth import hashear_password
from backend.startup_migrations import ensure_column


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.query(Usuario).delete()
    db.commit()
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    try:
        yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_login_case_insensitive(client):
    db = TestingSessionLocal()
    db.add(Usuario(email="test@example.com", hashed_password=hashear_password("secret")))
    db.commit()
    db.close()

    resp = client.post("/login", json={"email": "Test@Example.com", "password": "secret"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_nonexistent(client):
    resp = client.post("/login", json={"email": "nope@example.com", "password": "x"})
    assert resp.status_code == 401


def test_login_wrong_password(client):
    db = TestingSessionLocal()
    db.add(Usuario(email="test2@example.com", hashed_password=hashear_password("secret")))
    db.commit()
    db.close()
    resp = client.post("/login", json={"email": "test2@example.com", "password": "bad"})
    assert resp.status_code == 401


def test_login_db_error(monkeypatch, caplog):
    Base.metadata.create_all(bind=engine)

    def faulty_get_db():
        db = TestingSessionLocal()
        def bad_execute(*a, **k):
            raise SQLAlchemyError("boom")
        db.execute = bad_execute  # type: ignore
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = faulty_get_db
    try:
        with caplog.at_level("ERROR"):
            resp = TestClient(app).post(
                "/login", json={"email": "x@example.com", "password": "y"}
            )
        assert resp.status_code == 500
        assert "/login error" in caplog.text
    finally:
        app.dependency_overrides[get_db] = override_get_db


def test_health_db(client):
    resp = client.get("/health/db")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["engine"] == "sqlite"
    assert "sqlite" in data["dsn"]


def test_guard_creates_suspendido_and_login():
    engine2 = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine2)
    with engine2.begin() as conn:
        conn.execute(text("ALTER TABLE usuarios DROP COLUMN suspendido"))
    Session2 = sessionmaker(bind=engine2)

    def override_db():
        db = Session2()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        ensure_column(
            engine2,
            "usuarios",
            "suspendido",
            "ALTER TABLE usuarios ADD COLUMN suspendido BOOLEAN NOT NULL DEFAULT 0",
        )
        with Session2() as db:
            db.add(Usuario(email="foo@example.com", hashed_password=hashear_password("bar")))
            db.commit()
        resp = TestClient(app).post(
            "/login", json={"email": "foo@example.com", "password": "bar"}
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)

