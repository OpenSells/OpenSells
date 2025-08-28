from sqlalchemy import create_engine, text, inspect

from backend.startup_migrations import ensure_lead_tarea_auto_column


def test_migracion_auto_tarea():
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

    ensure_lead_tarea_auto_column(engine)

    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("lead_tarea")]
    assert "auto" in cols

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO lead_tarea (email, user_email_lower, texto, timestamp) VALUES ('a','a','t','1')"
            )
        )
        val = conn.execute(text("SELECT auto FROM lead_tarea")).scalar_one()
    assert val in (0, False)
