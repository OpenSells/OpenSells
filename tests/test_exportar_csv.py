import io
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db, Base
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
    assert response.status_code == 200

    df = pd.read_csv(io.BytesIO(response.content))

    # ✅ Verificar que no haya duplicados por Dominio
    assert len(df) == len(df.drop_duplicates(subset="Dominio"))

    # ✅ Verificar que no haya filas completamente vacías
    df_empty = df.dropna(how="all")
    assert len(df) == len(df_empty), "Hay filas completamente vacías"

    # ✅ Verificar que el CSV tiene al menos una fila de contenido
    assert len(df) >= 1
