import pytest
from sqlalchemy import text

from backend.utils import normalizar_nicho
from tests.helpers import auth


def _models():
    from backend.models import LeadExtraido, LeadInfoExtra, LeadTarea

    return LeadExtraido, LeadInfoExtra, LeadTarea


def _create_lead(db_session, email: str, dominio: str, nicho_visible: str = "Dentistas Sevilla"):
    LeadExtraido, _, _ = _models()

    lead = LeadExtraido(
        user_email=email,
        user_email_lower=email,
        dominio=dominio,
        url=f"https://{dominio}",
        nicho=normalizar_nicho(nicho_visible),
        nicho_original=nicho_visible,
        estado_contacto="pendiente",
    )
    db_session.add(lead)
    db_session.commit()
    return lead


@pytest.mark.usefixtures("db_session")
class TestLeadsCrudEndpoints:
    def test_info_extra_y_guardado(self, client, db_session):
        email = "crud1@example.com"
        dominio = "infoextra.com"
        headers = auth(client, email)

        lead = _create_lead(db_session, email, dominio)

        resp = client.get("/info_extra", headers=headers, params={"dominio": dominio})
        assert resp.status_code == 200
        data = resp.json()
        assert data["dominio"] == dominio
        assert data["estado_contacto"] == "pendiente"
        assert data["email"] == ""
        assert data["telefono"] == ""
        assert data["informacion"] == ""

        payload = {
            "dominio": dominio,
            "email": " contacto@example.com ",
            "telefono": " 123456789 ",
            "informacion": " Cliente interesado ",
        }
        save_resp = client.post("/guardar_info_extra", headers=headers, json=payload)
        assert save_resp.status_code in (200, 201)

        again = client.get("/info_extra", headers=headers, params={"dominio": dominio})
        assert again.status_code == 200
        updated = again.json()
        assert updated["email"] == "contacto@example.com"
        assert updated["telefono"] == "123456789"
        assert updated["informacion"] == "Cliente interesado"
        assert updated["nicho"] == lead.nicho

    def test_nota_lead_crea_y_listado(self, client, db_session):
        email = "crud2@example.com"
        dominio = "notas.com"
        headers = auth(client, email)

        _create_lead(db_session, email, dominio)

        resp = client.post(
            "/nota_lead",
            headers=headers,
            json={"dominio": dominio, "texto": "Revisar web"},
        )
        assert resp.status_code == 201
        nota_id = resp.json()["id"]

        info = client.get("/info_extra", headers=headers, params={"dominio": dominio})
        assert info.status_code == 200
        notas = info.json().get("notas", [])
        assert any(n["id"] == nota_id and n["texto"] == "Revisar web" for n in notas)

    def test_estado_chip_usa_endpoint_dominio(self, client, db_session):
        email = "crud3@example.com"
        dominio = "estado.com"
        headers = auth(client, email)

        lead = _create_lead(db_session, email, dominio)

        ok_resp = client.post(
            "/leads/estado_contacto",
            headers=headers,
            json={"dominio": dominio, "estado_contacto": "cerrado"},
        )
        assert ok_resp.status_code == 200
        assert ok_resp.json()["estado"] == "cerrado"

        LeadExtraido, _, _ = _models()
        updated = (
            db_session.query(LeadExtraido)
            .filter_by(user_email_lower=email, dominio=dominio)
            .one()
        )
        assert updated.estado_contacto == "cerrado"

        invalid_resp = client.post(
            "/leads/estado_contacto",
            headers=headers,
            json={"dominio": dominio, "estado_contacto": "en_progreso"},
        )
        assert invalid_resp.status_code == 400
        assert invalid_resp.json()["detail"] == "Estado inválido."

        shim_resp = client.patch(
            f"/leads/{lead.id}/estado_contacto",
            headers=headers,
            json={"estado_contacto": "fallido"},
        )
        assert shim_resp.status_code == 200
        refreshed = (
            db_session.query(LeadExtraido)
            .filter_by(user_email_lower=email, dominio=dominio)
            .one()
        )
        assert refreshed.estado_contacto == "fallido"

    def test_eliminar_lead_firma_antigua(self, client, db_session):
        email = "crud4@example.com"
        dominio = "borrar.com"
        headers = auth(client, email)

        lead = _create_lead(db_session, email, dominio)
        _, _, LeadTarea = _models()

        tarea = LeadTarea(
            email=email,
            user_email_lower=email,
            dominio=dominio,
            texto="Recordar llamada",
            fecha=None,
            completado=False,
            tipo="manual",
            nicho=lead.nicho,
            prioridad="media",
            auto=False,
        )
        db_session.add(tarea)
        db_session.commit()

        client.post(
            "/nota_lead",
            headers=headers,
            json={"dominio": dominio, "texto": "Nota temporal"},
        )
        client.post(
            "/guardar_info_extra",
            headers=headers,
            json={
                "dominio": dominio,
                "email": "a@b.com",
                "telefono": "600600600",
                "informacion": "Eliminar",
            },
        )

        delete_resp = client.delete(
            "/eliminar_lead",
            headers=headers,
            params={"nicho": lead.nicho, "dominio": dominio, "solo_de_este_nicho": True},
        )
        assert delete_resp.status_code == 200

        LeadExtraido, LeadInfoExtra, LeadTarea = _models()
        assert (
            db_session.query(LeadExtraido)
            .filter_by(user_email_lower=email, dominio=dominio)
            .count()
            == 0
        )
        assert (
            db_session.query(LeadTarea)
            .filter_by(user_email_lower=email, dominio=dominio)
            .count()
            == 0
        )
        assert (
            db_session.query(LeadInfoExtra)
            .filter_by(user_email_lower=email, dominio=dominio)
            .count()
            == 0
        )
        notas_count = db_session.execute(
            text(
                "SELECT COUNT(*) FROM lead_nota WHERE user_email_lower = :u AND dominio = :d"
            ),
            {"u": email, "d": dominio},
        ).scalar()
        assert notas_count == 0

        again = client.delete(
            "/eliminar_lead",
            headers=headers,
            params={"nicho": lead.nicho, "dominio": dominio, "solo_de_este_nicho": True},
        )
        assert again.status_code == 404
        assert again.json()["detail"] == "Lead no encontrado."
