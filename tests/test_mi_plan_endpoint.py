import uuid

from tests.test_plan_enforcement import auth, set_plan


def test_mi_plan_free_fields(client):
    email = f"free_fields_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    r = client.get("/mi_plan", headers=headers)
    data = r.json()
    assert data["plan"] == "free"
    limits = data["limits"]
    assert limits["lead_credits_month"] is None
    assert limits["searches_per_month"] == 4
    assert limits["csv_exports_per_month"] == 1
    assert limits["tasks_active_max"] == 3
    usage = data["usage"]
    assert usage["free_searches"]["remaining"] == 4
    assert usage["lead_credits"]["remaining"] is None


def test_mi_plan_starter_fields(client, db_session):
    email = f"starter_fields_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    r = client.get("/mi_plan", headers=headers)
    data = r.json()
    limits = data["limits"]
    assert data["plan"] == "starter"
    assert limits["lead_credits_month"] == 150
    assert limits["searches_per_month"] is None
    assert limits["csv_exports_per_month"] is None
    assert limits["tasks_active_max"] == 20


def test_mi_plan_usage_updates(client):
    email = f"usage_updates_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    client.post("/tareas", json={"texto": "a"}, headers=headers)
    client.post("/ia", json={"prompt": "hi"}, headers=headers)
    client.post("/buscar_leads", json={"nuevos": 5}, headers=headers)
    client.post("/exportar_csv", json={"filename": "a.csv"}, headers=headers)
    r = client.get("/mi_plan", headers=headers)
    data = r.json()
    usage = data["usage"]
    assert usage["tasks_active"]["current"] == 1
    assert usage["ai_messages"]["used_today"] == 1
    assert usage["free_searches"]["used"] == 1
    assert usage["csv_exports"]["used"] == 1


def test_mi_plan_without_usage_table(client, db_session):
    db_session.execute("DROP TABLE IF EXISTS usage_counters")
    db_session.commit()
    email = f"no_table_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    r = client.get("/mi_plan", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["usage"]["lead_credits"]["used"] == 0
    assert data.get("meta", {}).get("degraded") is True
    # recreate table for subsequent tests
    from backend.models import UsageCounter

    UsageCounter.__table__.create(db_session.bind)
    db_session.commit()
