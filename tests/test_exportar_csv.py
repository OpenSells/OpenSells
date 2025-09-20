from backend.core import db_introspection


class DummyUser:
    def __init__(self, user_id=1, email="user@example.com"):
        self.id = user_id
        self.email = email


def test_build_historial_insert_prefers_user_id(monkeypatch, db_session):
    def fake_get_columns(db, table_name):
        assert table_name == "historial"
        return {"user_id", "filename"}

    monkeypatch.setattr(db_introspection, "get_table_columns", fake_get_columns)

    sql, params = db_introspection.build_historial_insert(db_session, DummyUser(user_id=42))

    assert sql == "INSERT INTO historial (user_id, filename) VALUES (:uid, :filename)"
    assert params == {"uid": 42}


def test_build_historial_insert_uses_email_lower(monkeypatch, db_session):
    def fake_get_columns(db, table_name):
        assert table_name == "historial"
        return {"user_email_lower", "filename"}

    monkeypatch.setattr(db_introspection, "get_table_columns", fake_get_columns)

    sql, params = db_introspection.build_historial_insert(
        db_session, DummyUser(email="SomeOne@Example.com")
    )

    assert sql == "INSERT INTO historial (user_email_lower, filename) VALUES (:email_lower, :filename)"
    assert params == {"email_lower": "someone@example.com"}


def test_build_historial_insert_creates_column(monkeypatch, db_session):
    calls = {"ensure": 0}

    def fake_get_columns(db, table_name):
        assert table_name == "historial"
        return set()

    def fake_ensure(db):
        calls["ensure"] += 1

    monkeypatch.setattr(db_introspection, "get_table_columns", fake_get_columns)
    monkeypatch.setattr(db_introspection, "ensure_historial_user_email_lower", fake_ensure)

    sql, params = db_introspection.build_historial_insert(db_session, DummyUser())

    assert calls["ensure"] == 1
    assert sql == "INSERT INTO historial (user_email_lower, filename) VALUES (:email_lower, :filename)"
    assert params == {"email_lower": "user@example.com"}
