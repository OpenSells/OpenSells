from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.db import obtener_todas_tareas_pendientes_postgres


def test_vista_tareas_no_revienta():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE lead_tarea (
                    id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    user_email_lower TEXT NOT NULL,
                    dominio TEXT,
                    texto TEXT NOT NULL,
                    fecha TEXT,
                    completado BOOLEAN DEFAULT 0,
                    timestamp TEXT,
                    tipo TEXT,
                    nicho TEXT,
                    prioridad TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE leads_extraidos (
                    id INTEGER PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    user_email_lower TEXT NOT NULL,
                    url TEXT NOT NULL,
                    timestamp TEXT,
                    nicho TEXT NOT NULL,
                    nicho_original TEXT NOT NULL,
                    estado_contacto TEXT
                )
                """
            )
        )
    Session = sessionmaker(bind=engine)
    session = Session()

    datos = obtener_todas_tareas_pendientes_postgres("a", session)
    assert datos == []
