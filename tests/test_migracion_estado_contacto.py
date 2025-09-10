from sqlalchemy import create_engine, text, inspect

from backend.startup_migrations import ensure_estado_contacto_column


def test_migracion_estado_contacto():
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

    ensure_estado_contacto_column(engine)

    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("leads_extraidos")]
    assert "estado_contacto" in cols

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO leads_extraidos (user_email, user_email_lower, dominio, url, nicho, nicho_original) VALUES ('a','a','b','b','n','n')"
            )
        )
        val = conn.execute(text("SELECT estado_contacto FROM leads_extraidos")).scalar_one()
    assert val == "pendiente"
