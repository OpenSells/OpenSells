from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.db import obtener_leads_por_nicho


def test_listado_nichos_no_revienta():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE leads_extraidos (
                    id INTEGER PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    user_email_lower TEXT NOT NULL,
                    dominio TEXT NOT NULL,
                    url TEXT NOT NULL,
                    timestamp TEXT,
                    nicho TEXT NOT NULL,
                    nicho_original TEXT NOT NULL
                )
                """
            )
        )
    Session = sessionmaker(bind=engine)
    session = Session()

    datos = obtener_leads_por_nicho("a", "n", session)
    assert datos == []
