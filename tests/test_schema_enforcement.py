import pathlib, re, pytest
from sqlalchemy import text


def test_usuarios_email_unique_lower(db_session):
    rows = db_session.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname='public' AND tablename='usuarios'
          AND indexname='ix_usuarios_email_lower'
    """)).fetchall()
    assert rows and "UNIQUE" in rows[0][1].upper()


def test_user_usage_monthly_unique(db_session):
    rows = db_session.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid='user_usage_monthly'::regclass
          AND conname='uix_user_period'
    """)).fetchall()
    assert rows


def test_user_usage_monthly_columns(db_session):
    rows = db_session.execute(
        text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name='user_usage_monthly'
            """
        )
    ).fetchall()
    cols = {r[0] for r in rows}
    expected = {
        "id",
        "user_id",
        "period_yyyymm",
        "leads",
        "ia_msgs",
        "tasks",
        "csv_exports",
        "searches",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(cols)


def test_leads_extraidos_unique(db_session):
    rows = db_session.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid='leads_extraidos'::regclass
          AND conname='uix_leads_usuario_dominio'
    """)).fetchall()
    assert rows


def test_lead_estado_unique_constraint(db_session):
    db_session.execute(
        text(
            "INSERT INTO lead_estado (user_email_lower, dominio, estado) VALUES (:u, :d, :e)"
        ),
        {"u": "x@example.com", "d": "example.com", "e": "a"},
    )
    db_session.commit()
    with pytest.raises(Exception):
        db_session.execute(
            text(
                "INSERT INTO lead_estado (user_email_lower, dominio, estado) VALUES (:u, :d, :e)"
            ),
            {"u": "x@example.com", "d": "example.com", "e": "b"},
        )
        db_session.commit()
    db_session.rollback()


def test_no_sqlite_leftovers():
    root = pathlib.Path(".")
    bad = []
    for p in root.rglob("**/*.py"):
        if "tests" in p.parts:
            continue
        if "scripts/migrar_sqlite" in str(p) or "scripts/migrar_memoria_sqlite" in str(p):
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(sqlite://|historial\.db|aiosqlite)", txt):
            bad.append(str(p))
    assert not bad, f"Referencias a SQLite encontradas: {bad}"
