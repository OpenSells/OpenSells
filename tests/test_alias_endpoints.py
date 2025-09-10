import pytest


def _token(client):
    email = "alias@example.com"
    password = "secret"
    client.post("/register", json={"email": email, "password": password})
    r = client.post("/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_alias_endpoints(client):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    for path in ["/me", "/mi_plan", "/mi_memoria", "/mis_nichos"]:
        assert client.get(path, headers=headers).status_code == 200
        assert client.get(path).status_code == 401
