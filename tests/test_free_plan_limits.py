import importlib

from tests.helpers import auth, set_plan


def test_free_plan_allows_4_searches_then_blocks_5th(client):
    headers = auth(client, "free-limit@example.com")
    payload = {"nuevos": 3, "duplicados": 0}

    for _ in range(4):
        resp = client.post("/buscar_leads", json=payload, headers=headers)
        assert resp.status_code == 200

    resp = client.post("/buscar_leads", json=payload, headers=headers)
    assert resp.status_code == 403
    detail = resp.json().get("detail", {})
    assert detail.get("error") == "limit_exceeded"
    assert detail.get("resource") == "searches"
    assert detail.get("plan") == "free"
    assert detail.get("remaining") == 0


def test_free_plan_truncates_to_10_leads_per_search(client, monkeypatch):
    headers = auth(client, "free-truncate@example.com")
    main_module = importlib.import_module("backend.main")

    async def fake_scrape(domains):
        resultados = []
        for idx, domain in enumerate(domains):
            resultados.append(
                {
                    "dominio": domain,
                    "url": f"https://{domain}",
                    "email": None,
                    "telefono": None,
                    "origen": "test",
                    "idx": idx,
                }
            )
        return resultados

    monkeypatch.setattr(main_module, "scrape_domains", fake_scrape)

    urls = [f"https://site{idx}.com" for idx in range(12)]
    resp = client.post("/extraer_multiples", json={"urls": urls, "pais": "ES"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("truncated") is True
    assert len(data.get("resultados", [])) == 10
    dominios = [item.get("dominio") for item in data.get("resultados", [])]
    assert dominios == [f"site{idx}.com" for idx in range(10)]


def test_paid_plan_blocks_when_lead_credits_exhausted(client, db_session):
    from backend.core.plan_config import PLANES
    from backend.core.usage_service import UsageService
    from backend.models import Usuario

    email = "starter-limit@example.com"
    headers = auth(client, email)
    set_plan(db_session, email, "starter")

    user = db_session.query(Usuario).filter_by(email=email).first()
    assert user is not None

    plan_limit = PLANES["starter"].lead_credits_month or 0
    usage_svc = UsageService(db_session)
    period = usage_svc.get_period_yyyymm()
    usage_svc.increment(user.id, "leads", plan_limit, period)
    db_session.commit()

    resp = client.post("/buscar_leads", json={"nuevos": 5, "duplicados": 0}, headers=headers)
    assert resp.status_code == 403
    detail = resp.json().get("detail", {})
    assert detail.get("resource") == "lead_credits"
    assert detail.get("plan") == "starter"


def test_ai_daily_limit_resets_next_day(client, monkeypatch):
    headers = auth(client, "ai-limit@example.com")
    usage_helpers = importlib.import_module("backend.core.usage_helpers")
    main_module = importlib.import_module("backend.main")

    def day_one(_dt=None):
        return "20240101"

    def day_two(_dt=None):
        return "20240102"

    monkeypatch.setattr(usage_helpers, "day_key", day_one)
    monkeypatch.setattr(main_module, "day_key", day_one)

    for _ in range(5):
        resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
        assert resp.status_code == 200

    resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
    assert resp.status_code == 403
    detail = resp.json().get("detail", {})
    assert detail.get("resource") == "ai"
    assert detail.get("remaining") == 0

    monkeypatch.setattr(usage_helpers, "day_key", day_two)
    monkeypatch.setattr(main_module, "day_key", day_two)

    resp = client.post("/ia", json={"prompt": "hola"}, headers=headers)
    assert resp.status_code == 200
