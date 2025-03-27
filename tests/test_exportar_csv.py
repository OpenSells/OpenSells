import os
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
        "pais": "ES"
    }

    response = client.post("/exportar_csv", json=payload)
    assert response.status_code == 200

    # Extraer el path del archivo que viene en la respuesta
    filepath = response.headers.get("content-disposition")
    assert filepath is not None
    filename = filepath.split("filename=")[-1].strip('"')
    full_path = os.path.join("exports", filename)

    assert os.path.exists(full_path)

    # Leer el CSV generado
    df = pd.read_csv(full_path)

    # ✅ Verificar que no haya duplicados por URL y Email
    df_temp = df[["URL", "Emails"]].drop_duplicates()
    assert len(df) == len(df_temp), "Hay duplicados en el archivo CSV"

    # ✅ Verificar que no haya filas completamente vacías
    df_empty = df.dropna(how="all")
    assert len(df) == len(df_empty), "Hay filas completamente vacías"

    # ✅ Verificar que el CSV tiene al menos una fila de contenido
    assert len(df) >= 1
