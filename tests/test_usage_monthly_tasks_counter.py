import uuid

from tests.helpers import auth, set_plan

# UsageService and models imported lazily inside tests to avoid DB init at import time


def test_tasks_usage_counter(client, db_session):
    from backend.core.usage_service import UsageService
    from backend.models import Usuario, UserUsageMonthly

    email = f"usage_monthly_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "pro")
    client.post("/tareas", json={"texto": "a"}, headers=headers)
    client.post("/tareas", json={"texto": "b"}, headers=headers)
    user = db_session.query(Usuario).filter_by(email=email.lower()).first()
    period = UsageService(db_session).get_period_yyyymm()
    row = (
        db_session.query(UserUsageMonthly)
        .filter_by(user_id=user.id, period_yyyymm=period)
        .first()
    )
    assert row.tasks == 2
    r = client.get("/plan/quotas", headers=headers)
    assert r.json()["usage"]["tasks"]["used"] == 2


def test_tasks_quota_enforced(client):
    email = f"free_quota_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    for i in range(3):
        client.post("/tareas", json={"texto": str(i)}, headers=headers)
    r = client.post("/tareas", json={"texto": "x"}, headers=headers)
    assert r.status_code == 422
