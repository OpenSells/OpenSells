import streamlit as st
from typing import Tuple, Optional

from streamlit_app.utils import http_client
from streamlit_app.utils.cookies_utils import (
    get_auth_token,
    set_auth_token,
    clear_auth_token,
)


def ensure_session(require_auth: bool = False) -> Tuple[Optional[dict], Optional[str]]:
    """Devuelve (user, token). Restaura desde cookie si hace falta y valida con /me."""
    token = st.session_state.get("token") or get_auth_token()
    if not token:
        if require_auth:
            st.error("Token inválido o expirado. Inicia sesión nuevamente.")
            st.stop()
        return None, None

    st.session_state["token"] = token

    resp = http_client.get("/me", headers={"Authorization": f"Bearer {token}"})
    if resp is not None and resp.status_code == 200:
        user = resp.json()
        st.session_state["user"] = user
        set_auth_token(token)
        return user, token

    clear_session()
    if require_auth:
        st.error("Token inválido o expirado. Inicia sesión nuevamente.")
        st.stop()
    return None, None


def clear_session():
    """Limpia estado y cookies."""
    for k in ("token", "user", "csv_bytes", "csv_filename", "lead_actual"):
        st.session_state.pop(k, None)
    try:
        clear_auth_token()
    except Exception:
        pass


def logout_and_redirect(target: str = "/"):
    clear_session()
    st.experimental_set_query_params()
    try:
        st.switch_page("streamlit/Home.py")
    except Exception:
        try:
            st.switch_page("Home.py")
        except Exception:
            st.experimental_rerun()


def logout_button(label: str = "Cerrar sesión") -> None:
    if st.sidebar.button(label):
        logout_and_redirect("/")
