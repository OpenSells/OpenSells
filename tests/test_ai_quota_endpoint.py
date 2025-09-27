import importlib

from tests.helpers import auth, set_plan


def _freeze_day(monkeypatch, value: str = "20240201"):
    usage_helpers = importlib.import_module("backend.core.usage_helpers")
    main_module = importlib.import_module("backend.main")
    monkeypatch.setattr(usage_helpers, "day_key", lambda _dt=None: value)
    monkeypatch.setattr(main_module, "day_key", lambda _dt=None: value)


def test_ai_endpoint_returns_remaining_after_use(client, monkeypatch):
    headers = auth(client, "ai-quota-basic@example.com")
    _freeze_day(monkeypatch, "20240210")

    resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("remaining_today") == 9


def test_ai_endpoint_blocks_after_daily_limit(client, monkeypatch):
    headers = auth(client, "ai-quota-limit@example.com")
    _freeze_day(monkeypatch, "20240211")

    for _ in range(9):
        resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
        assert resp.status_code == 200

    resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("remaining_today") == 0

    resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
    assert resp.status_code == 403
    detail = resp.json().get("detail", {})
    assert detail.get("resource") == "ai"
    assert detail.get("remaining") == 0


def test_ai_endpoint_allows_unlimited_plan(client, db_session, monkeypatch):
    headers = auth(client, "ai-quota-unlimited@example.com")

    plan_config = importlib.import_module("backend.core.plan_config")
    monkeypatch.setitem(
        plan_config.PLANES,
        "infinite",
        plan_config.PlanConfig(
            type="paid",
            lead_credits_month=100,
            csv_unlimited=True,
            tasks_active_max=50,
            ai_daily_limit=None,
        ),
    )
    set_plan(db_session, "ai-quota-unlimited@example.com", "infinite")

    _freeze_day(monkeypatch, "20240212")

    for _ in range(3):
        resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("remaining_today") is None
