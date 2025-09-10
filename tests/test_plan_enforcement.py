
def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_plan_limit(client):
    headers = auth(client, "plan@example.com")
    assert client.post("/tareas", json={"texto": "a"}, headers=headers).status_code == 200
    assert client.post("/tareas", json={"texto": "b"}, headers=headers).status_code == 200
    r = client.post("/tareas", json={"texto": "c"}, headers=headers)
    assert r.status_code == 403
