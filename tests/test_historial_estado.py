def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_historial_and_estado_lead(client):
    headers = auth(client, "hist@example.com")

    r = client.post("/exportar_csv", json={"filename": "f.csv"}, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "filename": "f.csv"}
    r2 = client.get("/historial", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["historial"][0]["filename"] == "f.csv"

    r3 = client.post(
        "/estado_lead", json={"dominio": "example.com", "estado": "contactado"}, headers=headers
    )
    assert r3.status_code == 200
    r4 = client.post(
        "/estado_lead", json={"dominio": "example.com", "estado": "rechazado"}, headers=headers
    )
    assert r4.status_code == 200
    r5 = client.get("/estado_lead", params={"dominio": "example.com"}, headers=headers)
    assert r5.status_code == 200
    assert r5.json()["estado"] == "rechazado"
