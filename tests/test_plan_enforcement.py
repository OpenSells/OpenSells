import uuid


def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def set_plan(db_session, email, plan):
    from backend.models import Usuario

    u = db_session.query(Usuario).filter_by(email=email.lower()).first()
    u.plan = plan
    db_session.commit()


# --- Free plan tests -------------------------------------------------------

def test_free_searches_cap(client):
    email = f"free_search_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    for _ in range(4):
        assert client.post("/buscar_leads", json={"nuevos": 5}, headers=headers).status_code == 200
    r = client.post("/buscar_leads", json={"nuevos": 5}, headers=headers)
    assert r.status_code == 403


def test_free_search_lead_cap(client):
    email = f"free_leads_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    r = client.post("/buscar_leads", json={"nuevos": 20}, headers=headers)
    data = r.json()
    assert data["saved"] == 10
    assert data["truncated"] is True


def test_free_csv_cap(client):
    email = f"free_csv_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    assert client.post("/exportar_csv", json={"filename": "a.csv"}, headers=headers).status_code == 200
    r = client.post("/exportar_csv", json={"filename": "b.csv"}, headers=headers)
    assert r.status_code == 403


def test_free_tasks_active_cap(client):
    email = f"free_tasks_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    assert client.post("/tareas", json={"texto": "a"}, headers=headers).status_code == 200
    assert client.post("/tareas", json={"texto": "b"}, headers=headers).status_code == 200
    assert client.post("/tareas", json={"texto": "c"}, headers=headers).status_code == 200
    r = client.post("/tareas", json={"texto": "d"}, headers=headers)
    assert r.status_code == 403


def test_free_ai_daily(client):
    email = f"free_ai_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    for _ in range(5):
        assert client.post("/ia", json={"prompt": "hi"}, headers=headers).status_code == 200
    r = client.post("/ia", json={"prompt": "hi"}, headers=headers)
    assert r.status_code == 403


# --- Starter plan tests ----------------------------------------------------

def test_starter_credits_consumption(client, db_session):
    email = f"starter_credits_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    r = client.post("/buscar_leads", json={"nuevos": 35, "duplicados": 5}, headers=headers)
    assert r.json()["saved"] == 30
    r2 = client.get("/mi_plan", headers=headers)
    assert r2.json()["usage"]["lead_credits"]["used"] == 30


def test_starter_credits_truncation(client, db_session):
    email = f"starter_trunc_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    client.post("/buscar_leads", json={"nuevos": 130}, headers=headers)
    r = client.post("/buscar_leads", json={"nuevos": 30}, headers=headers)
    data = r.json()
    assert data["saved"] == 20
    assert data["truncated"] is True


def test_starter_csv_unlimited(client, db_session):
    email = f"starter_csv_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    for _ in range(3):
        assert client.post("/exportar_csv", json={"filename": "a.csv"}, headers=headers).status_code == 200


def test_starter_tasks_active_cap(client, db_session):
    email = f"starter_tasks_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    for i in range(20):
        assert client.post("/tareas", json={"texto": str(i)}, headers=headers).status_code == 200
    r = client.post("/tareas", json={"texto": "x"}, headers=headers)
    assert r.status_code == 403


def test_starter_ai_daily(client, db_session):
    email = f"starter_ai_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    for _ in range(20):
        assert client.post("/ia", json={"prompt": "hi"}, headers=headers).status_code == 200
    r = client.post("/ia", json={"prompt": "hi"}, headers=headers)
    assert r.status_code == 403
