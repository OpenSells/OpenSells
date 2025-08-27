import streamlit as st
from typing import Tuple, Optional
from streamlit_app.utils import http_client
from streamlit_app.utils.cookies_utils import (
    get_auth_token,
    set_auth_token,
    clear_auth_token,
)

# Inyecta el token existente al cliente HTTP al cargar el módulo
if "token" in st.session_state and st.session_state["token"]:
    http_client.set_auth_token(st.session_state["token"])


def require_auth_or_prompt() -> bool:
    """Check for a session token and prompt login when absent."""
    token = st.session_state.get("token")
    if not token:
        st.info("Inicia sesión para obtener acceso.")
        return False
    return True


def clear_session():
    for k in ("token", "user", "csv_bytes", "csv_filename", "lead_actual"):
        st.session_state.pop(k, None)
    try:
        clear_auth_token()
    except Exception:
        pass
    http_client.set_auth_token(None)


def ensure_session() -> Tuple[Optional[dict], Optional[str]]:
    """Devuelve (user, token). Restaura desde cookie, valida con /me y sincroniza estado."""
    token = st.session_state.get("token") or get_auth_token()
    if not token:
        return None, None

    st.session_state["token"] = token
    http_client.set_auth_token(token)
    resp = http_client.get("/me")
    if getattr(resp, "status_code", None) == 200:
        user = resp.json()
        st.session_state["user"] = user
        set_auth_token(token)
        return user, token

    # token inválido
    clear_session()
    return None, None


def logout_and_redirect(target: str = "streamlit/Home.py"):
    clear_session()
    try:
        st.switch_page(target)
    except Exception:
        st.rerun()
