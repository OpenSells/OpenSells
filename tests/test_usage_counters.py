import os
import uuid
from datetime import date

from tests.helpers import auth, set_plan

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

from backend.services.usage import UsageCounterService
from backend.config.plans import PLAN_LIMITS


def test_free_search_increments_searches(client, db_session):
    email = f"free_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "free")

    r = client.post("/buscar_leads", json={"nuevos": 1, "duplicados": 0}, headers=headers)
    assert r.status_code == 200

    r = client.get("/plan/usage", headers=headers)
    data = r.json()
    assert data["counters"]["searches_used"] == 1
    assert data["counters"]["leads_used"] == 0

    limit = PLAN_LIMITS["free"]["searches_per_month"]
    for _ in range(limit - 1):
        client.post("/buscar_leads", json={"nuevos": 1, "duplicados": 0}, headers=headers)
    r = client.post("/buscar_leads", json={"nuevos": 1, "duplicados": 0}, headers=headers)
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "quota_exceeded"
    assert body["limit_type"] == "searches_per_month"


def test_paid_leads_increment_and_limit(client, db_session):
    email = f"pro_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")

    limit = PLAN_LIMITS["starter"]["leads_per_month"]
    r = client.post(
        "/buscar_leads",
        json={"nuevos": limit, "duplicados": 0},
        headers=headers,
    )
    assert r.status_code == 200
    r = client.get("/plan/usage", headers=headers)
    data = r.json()
    assert data["counters"]["leads_used"] == limit
    assert data["counters"]["searches_used"] == 0

    r = client.post("/buscar_leads", json={"nuevos": 1, "duplicados": 0}, headers=headers)
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "quota_exceeded"
    assert body["limit_type"] == "leads_per_month"


def test_period_rollover(db_session):
    from backend.models import Usuario

    user = Usuario(email=f"roll_{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()

    svc = UsageCounterService(db_session)
    svc.increment_searches(user.id)
    current = svc.get_current_period_date()
    if current.month == 12:
        next_month = date(current.year + 1, 1, 1)
    else:
        next_month = date(current.year, current.month + 1, 1)
    row_next = svc.get_or_create_usage(user.id, next_month)
    assert row_next.leads_used == 0
    assert row_next.searches_used == 0
