def test_register_and_login(client):
    email = "login@example.com"
    password = "secret"
    r = client.post("/register", json={"email": email, "password": password})
    assert r.status_code == 200
    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r2 = client.get("/historial", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["historial"] == []
