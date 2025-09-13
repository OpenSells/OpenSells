import uuid
import pytest

from tests.test_plan_enforcement import auth


@pytest.mark.deprecated_endpoints
def test_tarea_lead_alias(client):
    email = f"legacy_{uuid.uuid4()}@example.com"
    headers = auth(client, email)
    r = client.post("/tarea_lead", json={"texto": "hola", "tipo": "general"}, headers=headers)
    assert r.status_code == 200
    lst = client.get("/tareas_pendientes", params={"tipo": "general", "solo_pendientes": "true"}, headers=headers)
    assert lst.status_code == 200
    data = lst.json()
    assert any(t["texto"] == "hola" for t in data)
