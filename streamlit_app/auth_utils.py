from __future__ import annotations

"""Helpers de autenticación y sesión."""

from typing import Optional, Tuple

import streamlit as st

from streamlit_app.utils import http_client


def save_token(token: Optional[str]) -> None:
    """Guarda el token en el ``session_state`` actual."""
    if token:
        st.session_state["token"] = token


def logout_button(label: str = "Cerrar sesión") -> None:
    """Muestra un botón en la barra lateral que limpia el token."""
    if st.sidebar.button(label):
        if "token" in st.session_state:
            del st.session_state["token"]
        st.rerun()


def ensure_token_and_user() -> Tuple[dict | None, str | None]:
    """Devuelve ``(user, token)`` si existe una sesión válida."""
    token = st.session_state.get("token")
    if not token:
        return None, None

    try:
        resp = http_client.get("/me", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return None, None
        user = resp.json()
        st.session_state["user"] = user
        return user, token
    except Exception:
        return None, None


def get_session_user(require_auth: bool = True) -> Tuple[Optional[str], Optional[dict]]:
    """Obtiene ``(token, user)`` desde ``st.session_state`` o intenta restaurarlos.

    Si ``require_auth`` es ``True`` y no hay usuario, se informa al usuario y se
    detiene la ejecución de la página.
    """
    token = st.session_state.get("token")
    user = st.session_state.get("user")

    if not user or not token:
        try:
            user, token = ensure_token_and_user()
        except Exception:
            token, user = None, None

    if require_auth and not user:
        st.info("Por favor, inicia sesión en la página **Home** para continuar.")
        st.stop()

    return token, user
