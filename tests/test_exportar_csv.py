import io
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_exportar_csv_limpeza():
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
