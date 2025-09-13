import uuid

from tests.helpers import auth


def test_tasks_aliases(client):
    email = f"alias_task_{uuid.uuid4()}@example.com"
    headers = auth(client, email)

    r = client.post(
        "/tarea_lead",
        json={"texto": "hola", "dominio": "ej.com"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["tipo"] == "lead"

    r2 = client.get(
        "/tareas_pendientes",
        params={"tipo": "general", "solo_pendientes": True},
        headers=headers,
    )
    assert r2.status_code == 200
