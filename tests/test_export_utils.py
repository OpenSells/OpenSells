import io
from datetime import datetime, timedelta, timezone, date
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.export_utils import fmt_fecha, dataframe_from_leads
from backend.database import Base, engine, SessionLocal
from backend.models import Usuario, LeadExtraido, Suscripcion
from backend.auth import hashear_password


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _seed():
    with SessionLocal() as db:
        user = Usuario(email="test@example.com", hashed_password=hashear_password("pw"))
        db.add(user)
        db.commit()
        db.refresh(user)
        base = datetime(2023, 1, 1, tzinfo=timezone.utc)
        leads = [
            LeadExtraido(
                user_email=user.email_lower,
                user_email_lower=user.email_lower,
                url="https://a.com",
                dominio="a.com",
                nicho="dentistas_madrid",
                nicho_original="Dentistas Madrid",
                timestamp=base + timedelta(days=2),
            ),
            LeadExtraido(
                user_email=user.email_lower,
                user_email_lower=user.email_lower,
                url="https://b.com",
                dominio="b.com",
                nicho="dentistas_madrid",
                nicho_original="Dentistas Madrid",
                timestamp=base,
            ),
        ]
        sus = Suscripcion(
            user_email_lower=user.email_lower,
            status="active",
            current_period_end=base + timedelta(days=30),
        )
        db.add_all(leads + [sus])
        db.commit()


@pytest.fixture()
def token(client):
    _seed()
    resp = client.post(
        "/login", data={"username": "test@example.com", "password": "pw"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_fmt_fecha_variants():
    aware = datetime(2023, 1, 1, tzinfo=timezone.utc)
    naive = datetime(2023, 1, 2)
    d = date(2023, 1, 3)
    s = "2023-01-04T12:00:00"
    assert fmt_fecha(aware) == "2023-01-01"
    assert fmt_fecha(naive) == "2023-01-02"
    assert fmt_fecha(d) == "2023-01-03"
    assert fmt_fecha(s) == "2023-01-04"
    assert fmt_fecha(None) == ""


def test_exportar_leads_nicho_csv(client, token):
    resp = client.get(
        "/exportar_leads_nicho",
        params={"nicho": "dentístas-madrid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename" in resp.headers["content-disposition"]
    assert resp.text.startswith("\ufeff")
    df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
    assert list(df.columns) == ["Dominio", "URL", "Fecha", "Nicho"]
    assert df.shape[0] == 2
    assert df.iloc[0]["Dominio"] == "a.com"
    assert df.iloc[0]["Fecha"] == "2023-01-03"
    assert df.iloc[1]["Dominio"] == "b.com"
    assert df.iloc[1]["Fecha"] == "2023-01-01"


def test_exportar_leads_nicho_empty(client, token):
    resp = client.get(
        "/exportar_leads_nicho",
        params={"nicho": "otro"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
    assert df.empty
    assert list(df.columns) == ["Dominio", "URL", "Fecha", "Nicho"]


def test_dataframe_dedup_and_order():
    leads = [
        {"dominio": "a.com", "timestamp": datetime(2023, 1, 1)},
        {"dominio": "b.com", "timestamp": datetime(2023, 1, 2)},
        {"dominio": "a.com", "timestamp": datetime(2023, 1, 3)},
    ]
    df = dataframe_from_leads(leads)
    assert list(df["Dominio"]) == ["a.com", "b.com"]
    assert list(df["Fecha"]) == ["2023-01-03", "2023-01-02"]
