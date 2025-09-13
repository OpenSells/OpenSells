
from tests.helpers import auth


def test_tareas_filters(client):
    headers = auth(client, "tareas@example.com")
    client.post("/tareas", json={"texto": "g", "tipo": "general"}, headers=headers)
    client.post(
        "/tareas",
        json={"texto": "n", "tipo": "nicho", "nicho": "ventas"},
        headers=headers,
    )
    client.post(
        "/tareas",
        json={"texto": "l", "tipo": "lead", "dominio": "ej.com", "completado": True},
        headers=headers,
    )

    r = client.get("/tareas", params={"tipo": "nicho"}, headers=headers)
    assert len(r.json()["tareas"]) == 1
    assert r.json()["tareas"][0]["texto"] == "n"

    r2 = client.get("/tareas", params={"nicho": "ventas"}, headers=headers)
    assert len(r2.json()["tareas"]) == 1
    assert r2.json()["tareas"][0]["texto"] == "n"

    r3 = client.get("/tareas", params={"dominio": "ej.com"}, headers=headers)
    assert len(r3.json()["tareas"]) == 1
    assert r3.json()["tareas"][0]["texto"] == "l"

    r4 = client.get("/tareas", params={"solo_pendientes": True}, headers=headers)
    assert len(r4.json()["tareas"]) == 2
