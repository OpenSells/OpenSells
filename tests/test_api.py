from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["mensaje"] == "¡Bienvenido al Wrapper Automático!"

def test_extraer_datos_valido():
    response = client.post("/extraer_datos", json={"url": "https://www.wikipedia.org/"})
    assert response.status_code == 200
    json_data = response.json()
    assert "url" in json_data
    assert "emails" in json_data
    assert "telefonos" in json_data
    assert "redes_sociales" in json_data

def test_extraer_datos_error():
    response = client.post("/extraer_datos", json={"url": "https://noexiste.abcde/"})
    assert response.status_code == 200
    json_data = response.json()
    assert "url" in json_data
    assert "error" in json_data

def test_extraer_multiples_varias_urls():
    payload = {
        "urls": ["https://www.wikipedia.org/", "https://noexiste.abcde/"],
        "pais": "ES"
    }
    response = client.post("/extraer_multiples", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert isinstance(json_data, list)
    assert len(json_data) == 2
    assert "url" in json_data[0]
