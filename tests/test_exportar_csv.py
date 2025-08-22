import io
import pandas as pd
from fastapi.testclient import TestClient
import pytest
from backend.main import app
from backend.database import Base, engine


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_exportar_csv_limpeza(client):
    payload = {
        "urls": [
            "https://www.wikipedia.org/",
            "https://www.wikipedia.org/",  # URL duplicada para probar limpieza
            "https://noexiste.abcde/"       # URL inválida
        ],
        "pais": "ES",
        "nicho": "test"
    }

    response = client.post("/exportar_csv", json=payload)
    assert response.status_code == 403
