import pytest

from backend.utils import normalizar_nicho
from tests.helpers import auth


def _lead_model():
    from backend.models import LeadExtraido

    return LeadExtraido


@pytest.mark.usefixtures("db_session")
class TestMoverLeadEndpoint:
    def test_move_lead_retorna_en_mis_nichos(self, client, db_session):
        headers = auth(client, "user1@example.com")
        dominio = "ejemplo.com"
        origen_visible = "Dentistas Murcia"
        destino_visible = "Dentistas Valencia"

        LeadExtraido = _lead_model()

        lead = LeadExtraido(
            user_email="user1@example.com",
            user_email_lower="user1@example.com",
            dominio=dominio,
            url="https://ejemplo.com",
            nicho=normalizar_nicho(origen_visible),
            nicho_original=origen_visible,
            estado_contacto="nuevo",
        )
        db_session.add(lead)
        db_session.commit()

        resp = client.post(
            "/mover_lead",
            headers=headers,
            json={
                "dominio": dominio,
                "origen": origen_visible,
                "destino": destino_visible,
                "actualizar_nicho_original": True,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["dominio"] == dominio
        assert data["de"] == origen_visible
        assert data["a"] == destino_visible

        moved = (
            db_session.query(LeadExtraido)
            .filter_by(user_email_lower="user1@example.com", dominio=dominio)
            .one()
        )
        assert moved.nicho == normalizar_nicho(destino_visible)
        assert moved.nicho_original == destino_visible

        mis_nichos = client.get("/mis_nichos", headers=headers)
        assert mis_nichos.status_code == 200
        data_nichos = mis_nichos.json()
        assert any(n["nicho"] == moved.nicho for n in data_nichos)
        assert any(n["nicho_original"] == destino_visible for n in data_nichos)

    def test_mover_lead_not_found(self, client):
        headers = auth(client, "user2@example.com")

        resp = client.post(
            "/mover_lead",
            headers=headers,
            json={
                "dominio": "no-existe.com",
                "nicho_origen": "Nicho Fantasma",
                "nicho_destino": "Nuevo Nicho",
            },
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Lead no encontrado en el nicho de origen."

    def test_mover_lead_conflict_duplicado(self, client, db_session):
        headers = auth(client, "user3@example.com")
        dominio = "otro.com"
        origen_visible = "Dentistas Murcia"
        nicho_existente = "Dentistas Sevilla"

        LeadExtraido = _lead_model()

        lead = LeadExtraido(
            user_email="user3@example.com",
            user_email_lower="user3@example.com",
            dominio=dominio,
            url="https://otro.com",
            nicho=normalizar_nicho(nicho_existente),
            nicho_original=nicho_existente,
            estado_contacto="nuevo",
        )
        db_session.add(lead)
        db_session.commit()

        resp = client.post(
            "/mover_lead",
            headers=headers,
            json={
                "dominio": dominio,
                "nicho_origen": origen_visible,
                "nicho_destino": "Dentistas Valencia",
            },
        )

        assert resp.status_code == 409
        detail = resp.json().get("detail", "")
        assert "El lead ya existe en el nicho" in detail
        assert nicho_existente in detail
