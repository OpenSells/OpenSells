import pytest

from backend.utils import normalizar_nicho
from tests.helpers import auth


def _models():
    from backend.models import LeadExtraido, LeadTarea

    return LeadExtraido, LeadTarea


def _create_lead(db_session, email: str, dominio: str, nicho_visible: str = "Dentistas Sevilla"):
    LeadExtraido, _ = _models()

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
    def test_info_extra_ok(self, client, db_session):
        email = "crud1@example.com"
        dominio = "infoextra.com"
        headers = auth(client, email)

        lead = _create_lead(db_session, email, dominio)
        _, LeadTarea = _models()

        tareas = [
            LeadTarea(
                email=email,
                user_email_lower=email,
                dominio=dominio,
                texto="Llamar",
                fecha=None,
                completado=False,
                tipo="manual",
                nicho=lead.nicho,
                prioridad="media",
                auto=False,
            ),
            LeadTarea(
                email=email,
                user_email_lower=email,
                dominio=dominio,
                texto="Enviar email",
                fecha=None,
                completado=False,
                tipo="manual",
                nicho=lead.nicho,
                prioridad="media",
                auto=False,
            ),
            LeadTarea(
                email=email,
                user_email_lower=email,
                dominio=dominio,
                texto="Revisión",
                fecha=None,
                completado=True,
                tipo="manual",
                nicho=lead.nicho,
                prioridad="media",
                auto=False,
            ),
        ]
        db_session.add_all(tareas)
        db_session.commit()

        for texto in ("Primera nota", "Segunda nota"):
            resp = client.post(
                "/nota_lead",
                headers=headers,
                json={"dominio": dominio, "texto": texto},
            )
            assert resp.status_code == 201

        resp = client.get("/info_extra", headers=headers, params={"dominio": dominio})
        assert resp.status_code == 200
        data = resp.json()
        assert data["dominio"] == dominio
        assert data["estado_contacto"] == "pendiente"
        assert data["tareas_totales"] == 3
        assert data["tareas_pendientes"] == 2
        assert len(data.get("notas", [])) == 2

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

    def test_estado_lead_ok_y_validacion(self, client, db_session):
        email = "crud3@example.com"
        dominio = "estado.com"
        headers = auth(client, email)

        _create_lead(db_session, email, dominio)

        ok_resp = client.patch(
            "/estado_lead",
            headers=headers,
            json={"dominio": dominio, "estado": "contactado"},
        )
        assert ok_resp.status_code == 200
        data = ok_resp.json()
        assert data["estado"] == "contactado"

        LeadExtraido, _ = _models()
        updated = (
            db_session.query(LeadExtraido)
            .filter_by(user_email_lower=email, dominio=dominio)
            .one()
        )
        assert updated.estado_contacto == "contactado"

        invalid_resp = client.patch(
            "/estado_lead",
            headers=headers,
            json={"dominio": dominio, "estado": "en_progreso"},
        )
        assert invalid_resp.status_code == 400
        assert invalid_resp.json()["detail"] == "Estado inválido."

    def test_eliminar_lead_ok_y_404(self, client, db_session):
        email = "crud4@example.com"
        dominio = "borrar.com"
        headers = auth(client, email)

        lead = _create_lead(db_session, email, dominio)
        _, LeadTarea = _models()

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

        resp_nota = client.post(
            "/nota_lead",
            headers=headers,
            json={"dominio": dominio, "texto": "Nota temporal"},
        )
        assert resp_nota.status_code == 201

        delete_resp = client.delete(
            "/eliminar_lead",
            headers=headers,
            params={"dominio": dominio, "solo_de_este_nicho": True},
        )
        assert delete_resp.status_code == 200

        LeadExtraido, LeadTarea = _models()
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

        again = client.delete(
            "/eliminar_lead",
            headers=headers,
            params={"dominio": dominio, "solo_de_este_nicho": True},
        )
        assert again.status_code == 404
        assert again.json()["detail"] == "Lead no encontrado."
