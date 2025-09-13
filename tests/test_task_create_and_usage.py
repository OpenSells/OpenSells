import uuid

from tests.helpers import auth, set_plan


def test_create_task_and_usage(client, db_session):
    from backend.core.usage_service import UsageService
    from backend.models import Usuario, UserUsageMonthly

    email = f"task_usage_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "pro")
    r = client.post("/tareas", json={"texto": "hola"}, headers=headers)
    assert r.status_code == 201
    r = client.get("/tareas", headers=headers)
    assert any(t["texto"] == "hola" for t in r.json()["tareas"])
    user = db_session.query(Usuario).filter_by(email=email.lower()).first()
    period = UsageService(db_session).get_period_yyyymm()
    row = (
        db_session.query(UserUsageMonthly)
        .filter_by(user_id=user.id, period_yyyymm=period)
        .first()
    )
    assert row and row.tasks == 1


def test_usage_ensure_row_idempotent(db_session):
    from backend.core.usage_service import UsageService
    from backend.models import Usuario, UserUsageMonthly

    svc = UsageService(db_session)
    user = Usuario(email=f"idem_{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    period = svc.get_period_yyyymm()
    svc.ensure_row(user.id, period)
    svc.ensure_row(user.id, period)
    rows = (
        db_session.query(UserUsageMonthly)
        .filter_by(user_id=user.id, period_yyyymm=period)
        .all()
    )
    assert len(rows) == 1


def test_task_quota_limit_free(client):
    email = f"task_quota_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    for i in range(3):
        client.post("/tareas", json={"texto": str(i)}, headers=headers)
    r = client.post("/tareas", json={"texto": "extra"}, headers=headers)
    assert r.status_code == 422
    assert "Tareas máximas" in r.json()["detail"]
