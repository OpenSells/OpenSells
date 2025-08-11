import os
import streamlit as st
import requests
from dotenv import load_dotenv
from cache_utils import limpiar_cache
from cookies_utils import (
    get_auth_token,
    get_auth_email,
    clear_auth_cookies,
)

load_dotenv()


def _safe_secret(name: str, default=None):
    """Safely retrieve configuration from env or Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")
ENV = _safe_secret("ENV")


def ensure_token_and_user() -> None:
    if "token" not in st.session_state:
        token = get_auth_token()
        if token:
            st.session_state.token = token
            if "email" not in st.session_state:
                st.session_state.email = get_auth_email()

    if "token" in st.session_state:
        if "usuario" not in st.session_state:
            try:
                r = requests.get(
                    f"{BACKEND_URL}/usuario_actual",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    st.session_state.usuario = r.json()
                else:
                    st.session_state.clear()
            except Exception:
                pass

    if ENV == "dev":
        st.write("DEBUG token in session:", "token" in st.session_state)
        st.write("DEBUG token from cookies:", get_auth_token())


def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión"):
        limpiar_cache()
        clear_auth_cookies()
        st.session_state.clear()
        st.experimental_set_query_params()
        try:
            st.switch_page("pages/1_Busqueda.py")
        except Exception:
            pass
        st.rerun()
