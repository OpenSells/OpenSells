from __future__ import annotations

import os
from typing import Any, Dict

import requests
import streamlit as st

from streamlit_app.utils.auth_session import get_auth_token


def _resolve_backend_url() -> str:
    env_value = os.getenv("BACKEND_URL")
    if env_value:
        return env_value
    try:
        secret_value = st.secrets.get("BACKEND_URL")
        if secret_value:
            return secret_value
    except Exception:
        pass
    return "http://127.0.0.1:8000"


BACKEND_URL = _resolve_backend_url()


def _headers() -> Dict[str, str]:
    token = get_auth_token() or st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_info_extra(dominio: str) -> Dict[str, Any] | None:
    try:
        r = requests.get(
            f"{BACKEND_URL}/info_extra",
            params={"dominio": dominio},
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        st.error(f"Error al cargar info extra ({exc}).")
        return None

    if r.status_code == 200:
        return r.json()
    if r.status_code == 404:
        st.warning("Lead no encontrado.")
    else:
        st.error(f"Error al cargar info extra ({r.status_code}).")
    return None


def api_nota_lead(dominio: str, texto: str) -> None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/nota_lead",
            json={"dominio": dominio, "texto": texto},
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        st.error(f"Error al añadir nota ({exc}).")
        return

    if r.status_code in (200, 201):
        st.success("Nota añadida.")
        st.rerun()
        return
    if r.status_code == 404:
        st.error("Lead no encontrado para añadir nota.")
    else:
        st.error(f"Error al añadir nota ({r.status_code}).")


def api_estado_lead(dominio: str, estado: str) -> None:
    try:
        r = requests.patch(
            f"{BACKEND_URL}/estado_lead",
            json={"dominio": dominio, "estado": estado},
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        st.error(f"Error al actualizar estado ({exc}).")
        return

    if r.status_code == 200:
        st.success(f"Estado actualizado a '{estado}'.")
        st.rerun()
        return
    if r.status_code == 404:
        st.error("Lead no encontrado.")
    elif r.status_code == 400:
        st.error("Estado inválido.")
    else:
        st.error(f"Error al actualizar estado ({r.status_code}).")


def api_eliminar_lead(dominio: str, solo_de_este_nicho: bool = True) -> None:
    try:
        r = requests.delete(
            f"{BACKEND_URL}/eliminar_lead",
            params={"dominio": dominio, "solo_de_este_nicho": str(solo_de_este_nicho)},
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        st.error(f"Error al eliminar lead ({exc}).")
        return

    if r.status_code == 200:
        st.success("Lead eliminado.")
        st.rerun()
        return
    if r.status_code == 404:
        st.warning("Lead no encontrado o ya eliminado.")
    else:
        st.error(f"Error al eliminar lead ({r.status_code}).")
