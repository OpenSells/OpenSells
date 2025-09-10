
def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_isolation(client):
    h1 = auth(client, "tenant1@example.com")
    h2 = auth(client, "tenant2@example.com")

    client.post("/tareas", json={"texto": "t1"}, headers=h1)
    client.post("/tareas", json={"texto": "t2"}, headers=h2)

    r1 = client.get("/tareas", headers=h1)
    r2 = client.get("/tareas", headers=h2)

    assert len(r1.json()["tareas"]) == 1
    assert len(r2.json()["tareas"]) == 1
    assert r1.json()["tareas"][0]["texto"] == "t1"
    assert r2.json()["tareas"][0]["texto"] == "t2"
