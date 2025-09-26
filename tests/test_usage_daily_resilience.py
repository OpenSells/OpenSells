import uuid

from sqlalchemy import text

from tests.conftest import run_alembic_upgrade
from tests.helpers import auth


def test_mi_plan_returns_usage_with_daily_counts(client):
    email = f"daily_ok_{uuid.uuid4()}@example.com"
    headers = auth(client, email)

    response = client.get("/mi_plan", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["plan"] == "free"
    assert "limits" in data
    assert "usage" in data
    usage = data["usage"]

    assert "ia_msgs" in usage
    assert usage["ia_msgs"]["used"] == 0
    assert usage.get("mensajes_ia", 0) == 0


def test_mi_plan_survives_missing_daily_table(client, db_session, pg_url):
    email = f"daily_missing_{uuid.uuid4()}@example.com"
    headers = auth(client, email)

    db_session.execute(text("DROP TABLE IF EXISTS user_usage_daily CASCADE"))
    db_session.commit()

    try:
        response = client.get("/mi_plan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        usage = data["usage"]
        assert usage.get("mensajes_ia", 0) == 0
        assert usage["ia_msgs"]["used"] == 0
    finally:
        run_alembic_upgrade(pg_url)


def test_daily_usage_increment_flow(client, db_session):
    from backend.models import Usuario
    from backend.core.usage_service import UsageDailyService

    email = f"daily_increment_{uuid.uuid4()}@example.com"
    headers = auth(client, email)

    first = client.get("/mi_plan", headers=headers).json()
    assert first["usage"]["ia_msgs"]["used"] == 0

    user = db_session.query(Usuario).filter_by(email=email.lower()).first()
    svc = UsageDailyService(db_session)
    svc.increment(user.id, "ia_msgs", amount=2)
    db_session.commit()

    after = client.get("/mi_plan", headers=headers).json()
    assert after["usage"]["ia_msgs"]["used"] >= 2
    assert after["usage"].get("mensajes_ia", 0) >= 2


def test_mi_plan_survives_missing_monthly_table(client, db_session, pg_url):
    email = f"monthly_missing_{uuid.uuid4()}@example.com"
    headers = auth(client, email)

    db_session.execute(text("DROP TABLE IF EXISTS user_usage_monthly CASCADE"))
    db_session.commit()

    try:
        response = client.get("/mi_plan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        usage = data["usage"]
        assert usage["leads"]["used"] == 0
        assert usage["tasks"]["used"] == 0
    finally:
        run_alembic_upgrade(pg_url)
