import uuid

from tests.test_plan_enforcement import auth, set_plan


def test_plan_quotas_pro(client, db_session):
    email = f"pro_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "pro")
    r = client.get("/plan/quotas", headers=headers)
    data = r.json()
    assert data["plan"] == "pro"
    assert data["limits"]["tasks_active_max"] == 100


def test_alias_endpoints_return_200(client):
    email = f"alias_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    paths = [
        "/usage",
        "/limits",
        "/stats/usage",
        "/me/usage",
        "/subscription/summary",
        "/billing/summary",
        "/stripe/subscription",
    ]
    for path in paths:
        assert client.get(path, headers=headers).status_code == 200


def test_usage_remaining(client):
    email = f"usage_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    client.post("/tareas", json={"texto": "a"}, headers=headers)
    r = client.get("/plan/quotas", headers=headers)
    data = r.json()
    assert data["usage"]["tasks_active"]["current"] == 1
    assert data["remaining"]["tasks_active"] == data["limits"]["tasks_active_max"] - 1


def test_task_creation_and_limit(client, db_session):
    email_pro = f"protask_{uuid.uuid4()}@example.com"
    headers_pro = auth(client, email_pro)
    set_plan(db_session, email_pro, "pro")
    assert client.post("/tareas", json={"texto": "hola"}, headers=headers_pro).status_code == 200

    email_free = f"freetask_{uuid.uuid4()}@example.com"
    headers_free = auth(client, email_free)
    for i in range(3):
        assert client.post("/tareas", json={"texto": str(i)}, headers=headers_free).status_code == 200
    r = client.post("/tareas", json={"texto": "x"}, headers=headers_free)
    assert r.status_code == 403
    assert r.json()["detail"]["error"] == "limit_exceeded"
