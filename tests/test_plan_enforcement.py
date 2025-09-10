import pytest


def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# -------- Free plan tests ---------


def test_free_searches_cap(client):
    headers = auth(client, "free1@example.com")
    payload = {"leads": ["a.com"]}
    for i in range(4):
        assert client.post("/buscar_leads", json=payload, headers=headers).status_code == 200
    r = client.post("/buscar_leads", json=payload, headers=headers)
    assert r.status_code == 403


def test_free_search_lead_cap(client):
    headers = auth(client, "free2@example.com")
    leads = [f"{i}.com" for i in range(15)]
    r = client.post("/buscar_leads", json={"leads": leads}, headers=headers)
    data = r.json()
    assert r.status_code == 200
    assert data["saved"] == 10
    assert data["truncated"] is True


def test_free_csv_cap(client):
    headers = auth(client, "free3@example.com")
    assert client.post("/exportar_csv", json={"filename": "a"}, headers=headers).status_code == 200
    r = client.post("/exportar_csv", json={"filename": "b"}, headers=headers)
    assert r.status_code == 403


def test_free_tasks_active_cap(client):
    headers = auth(client, "free4@example.com")
    for i in range(3):
        assert client.post("/tareas", json={"texto": str(i)}, headers=headers).status_code == 200
    r = client.post("/tareas", json={"texto": "boom"}, headers=headers)
    assert r.status_code == 403


def test_free_ai_daily(client):
    headers = auth(client, "free5@example.com")
    for _ in range(5):
        assert client.post("/ia", headers=headers).status_code == 200
    r = client.post("/ia", headers=headers)
    assert r.status_code == 403


# -------- Starter plan tests ---------


def starter_headers(client, db_session, email="starter@example.com"):
    headers = auth(client, email)
    user = db_session.execute(
        "select id from usuarios where email = :e", {"e": email}
    ).fetchone()
    db_session.execute(
        "update usuarios set plan='starter' where id=:id", {"id": user.id}
    )
    db_session.commit()
    return headers


def test_starter_credits_consumption(client, db_session):
    headers = starter_headers(client, db_session, "starter1@example.com")
    leads = [f"{i}.com" for i in range(30)] + [f"{i}.com" for i in range(5)]
    r = client.post("/buscar_leads", json={"leads": leads}, headers=headers)
    data = r.json()
    assert data["saved"] == 30
    assert data["duplicates"] == 5
    mp = client.get("/mi_plan", headers=headers).json()
    assert mp["usage"]["lead_credits"]["used"] == 30


def test_starter_credits_truncation(client, db_session):
    headers = starter_headers(client, db_session, "starter2@example.com")
    leads1 = [f"a{i}.com" for i in range(130)]
    client.post("/buscar_leads", json={"leads": leads1}, headers=headers)
    leads2 = [f"b{i}.com" for i in range(30)]
    r = client.post("/buscar_leads", json={"leads": leads2}, headers=headers)
    data = r.json()
    assert data["saved"] == 20
    assert data["truncated"] is True
    mp = client.get("/mi_plan", headers=headers).json()
    assert mp["usage"]["lead_credits"]["remaining"] == 0


def test_starter_csv_unlimited(client, db_session):
    headers = starter_headers(client, db_session, "starter3@example.com")
    for i in range(3):
        assert (
            client.post("/exportar_csv", json={"filename": str(i)}, headers=headers).status_code
            == 200
        )


def test_starter_tasks_active_cap(client, db_session):
    headers = starter_headers(client, db_session, "starter4@example.com")
    for i in range(20):
        assert client.post("/tareas", json={"texto": str(i)}, headers=headers).status_code == 200
    r = client.post("/tareas", json={"texto": "boom"}, headers=headers)
    assert r.status_code == 403


def test_starter_ai_daily(client, db_session):
    headers = starter_headers(client, db_session, "starter5@example.com")
    for _ in range(20):
        assert client.post("/ia", headers=headers).status_code == 200
    r = client.post("/ia", headers=headers)
    assert r.status_code == 403
