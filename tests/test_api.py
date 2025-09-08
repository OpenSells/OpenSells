from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, get_db
import backend.models  # ensure models imported
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["mensaje"] == "¡Bienvenido al Wrapper Automático!"

def test_extraer_datos_valido():
    response = client.post("/extraer_datos", json={"url": "https://www.wikipedia.org/"})
    assert response.status_code == 200
    json_data = response.json()
    assert "resultado" in json_data
    assert "url" in json_data["resultado"]

def test_extraer_datos_error():
    response = client.post("/extraer_datos", json={"url": "https://noexiste.abcde/"})
    assert response.status_code == 200
    json_data = response.json()
    assert "resultado" in json_data
    assert "url" in json_data["resultado"]
    assert "error" in json_data["resultado"]

def test_extraer_multiples_varias_urls():
    payload = {
        "urls": ["https://www.wikipedia.org/", "https://noexiste.abcde/"],
        "pais": "ES"
    }
    response = client.post("/extraer_multiples", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert isinstance(json_data.get("resultados"), list)
    assert len(json_data["resultados"]) == 2
    assert "Dominio" in json_data["resultados"][0]
