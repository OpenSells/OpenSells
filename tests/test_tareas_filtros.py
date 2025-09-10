
def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_tareas_filters(client):
    headers = auth(client, "tareas@example.com")
    client.post("/tareas", json={"texto": "uno", "nicho": "ventas"}, headers=headers)
    client.post("/tareas", json={"texto": "dos", "nicho": "marketing", "completado": True}, headers=headers)

    r = client.get("/tareas", params={"completado": False}, headers=headers)
    assert len(r.json()["tareas"]) == 1
    assert r.json()["tareas"][0]["texto"] == "uno"

    r2 = client.get("/tareas", params={"nicho": "marketing"}, headers=headers)
    assert len(r2.json()["tareas"]) == 1
    assert r2.json()["tareas"][0]["texto"] == "dos"
