from sqlalchemy import text

from tests.helpers import auth


def test_guardar_info_extra_upsert(client, db_session):
    headers = auth(client, "notes@example.com")

    payload = {
        "dominio": "Mi-Dominio.com",
        "email": "contacto@mi-dominio.com",
        "telefono": "+34 600 000 000",
        "informacion": "Nota inicial",
    }
    resp = client.post("/guardar_info_extra", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text

    consulta = client.get(
        "/info_extra", params={"dominio": "mi-dominio.com"}, headers=headers
    )
    assert consulta.status_code == 200
    data = consulta.json()
    assert data["informacion"] == "Nota inicial"
    assert data["email"] == "contacto@mi-dominio.com"
    assert data["telefono"] == "+34 600 000 000"

    # Actualización parcial para validar el ON CONFLICT
    resp = client.post(
        "/guardar_info_extra",
        json={"dominio": "mi-dominio.com", "informacion": "Nota actualizada"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    again = client.get(
        "/info_extra", params={"dominio": "MI-DOMINIO.COM"}, headers=headers
    )
    assert again.status_code == 200
    data = again.json()
    assert data["informacion"] == "Nota actualizada"
    assert data["email"] == "contacto@mi-dominio.com"
    assert data["telefono"] == "+34 600 000 000"

    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
              FROM lead_info_extra
             WHERE user_email_lower = :user
               AND dominio = :dominio
            """
        ),
        {"user": "notes@example.com", "dominio": "mi-dominio.com"},
    ).scalar_one()
    assert count == 1


def test_patch_estado_contacto_creates_single_row(client, db_session):
    headers = auth(client, "estado@example.com")

    alta = client.post(
        "/añadir_lead_manual",
        json={
            "dominio": "estado.com",
            "nicho": "Consultoría",
            "email": "info@estado.com",
        },
        headers=headers,
    )
    assert alta.status_code == 200, alta.text

    lead_id = db_session.execute(
        text(
            """
            SELECT id
              FROM leads_extraidos
             WHERE user_email_lower = :user
               AND dominio = :dominio
            """
        ),
        {"user": "estado@example.com", "dominio": "estado.com"},
    ).scalar_one()

    cambio = client.patch(
        f"/leads/{lead_id}/estado_contacto",
        json={"estado_contacto": "contactado"},
        headers=headers,
    )
    assert cambio.status_code == 200, cambio.text
    assert cambio.json()["ok"] is True

    post = db_session.execute(
        text(
            """
            SELECT estado_contacto
              FROM leads_extraidos
             WHERE id = :lead_id
            """
        ),
        {"lead_id": lead_id},
    ).scalar_one()
    assert post == "contactado"

    estado_fila = db_session.execute(
        text(
            """
            SELECT estado
              FROM lead_estado
             WHERE user_email_lower = :user
               AND dominio = :dominio
            """
        ),
        {"user": "estado@example.com", "dominio": "estado.com"},
    ).scalar_one()
    assert estado_fila == "contactado"

    # Segundo cambio: debe actualizar sin crear duplicados
    cambio2 = client.patch(
        f"/leads/{lead_id}/estado_contacto",
        json={"estado_contacto": "cerrado"},
        headers=headers,
    )
    assert cambio2.status_code == 200, cambio2.text

    estado_final = db_session.execute(
        text(
            """
            SELECT estado
              FROM lead_estado
             WHERE user_email_lower = :user
               AND dominio = :dominio
            """
        ),
        {"user": "estado@example.com", "dominio": "estado.com"},
    ).scalar_one()
    assert estado_final == "cerrado"

    total_rows = db_session.execute(
        text(
            """
            SELECT COUNT(*)
              FROM lead_estado
             WHERE user_email_lower = :user
               AND dominio = :dominio
            """
        ),
        {"user": "estado@example.com", "dominio": "estado.com"},
    ).scalar_one()
    assert total_rows == 1
