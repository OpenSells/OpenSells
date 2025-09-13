import uuid

import uuid

from tests.test_plan_enforcement import auth, set_plan


def test_mi_plan_free_fields(client):
    email = f"free_fields_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    r = client.get("/mi_plan", headers=headers)
    data = r.json()
    assert data["plan"] == "free"
    assert data["tareas_max"] == 4
    assert data["ia_mensajes"] == 5
    assert data["csv_exportacion"] is False


def test_mi_plan_starter_fields(client, db_session):
    email = f"starter_fields_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")
    r = client.get("/mi_plan", headers=headers)
    data = r.json()
    assert data["plan"] == "starter"
    assert data["tareas_max"] == 20
    assert data["ia_mensajes"] == 20
    assert data["csv_exportacion"] is True


def test_mi_plan_usage_updates(client):
    email = f"usage_updates_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    client.post("/tareas", json={"texto": "a"}, headers=headers)
    client.post("/ia", json={"prompt": "hi"}, headers=headers)
    client.post("/buscar_leads", json={"nuevos": 5}, headers=headers)
    r = client.get("/mi_plan", headers=headers)
    data = r.json()
    assert data["tareas_usadas_mes"] == 1
    assert data["ia_usados_mes"] == 1
    assert data["leads_usados_mes"] == 5


