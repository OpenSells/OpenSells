import os
import time
import streamlit as st
import requests
from streamlit import st_autorefresh
from streamlit_js_eval import streamlit_js_eval
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

INACTIVITY_MINUTES = 30  # tiempo de inactividad permitido


def _clear_auth_state(rerun: bool = False) -> None:
    """Borra credenciales de sesión, cookies y localStorage."""

    limpiar_cache()
    clear_auth_cookies()
    try:
        streamlit_js_eval(
            js_expressions="""
            localStorage.removeItem('wrapper_token');
            localStorage.removeItem('wrapper_email');
            localStorage.removeItem('lastActivity');
            """,
            key="js_clear_auth",
        )
    except Exception:
        pass
    st.session_state.clear()
    if rerun:
        st.experimental_set_query_params()
        st.rerun()


def _check_inactividad() -> None:
    """Comprueba si el usuario ha estado inactivo demasiado tiempo."""

    if "token" not in st.session_state:
        return
    try:
        last_ts = streamlit_js_eval(
            js_expressions="""
            (function(){
                const key='lastActivity';
                const now = Date.now();
                if(!window._activityListenersAdded){
                    window._activityListenersAdded = true;
                    const update = () => localStorage.setItem(key, Date.now());
                    ['click','mousemove','keydown','scroll'].forEach(e=>document.addEventListener(e, update));
                    if(!localStorage.getItem(key)) update();
                }
                return localStorage.getItem(key);
            })();
            """,
            key="activity_ts",
        )
        if last_ts:
            now_ms = int(time.time() * 1000)
            if now_ms - int(last_ts) > INACTIVITY_MINUTES * 60 * 1000:
                _clear_auth_state(rerun=True)
    except Exception:
        pass


def ensure_token_and_user() -> None:
    if "token" not in st.session_state:
        token = None
        email = None
        try:
            token = streamlit_js_eval(
                js_expressions="window.localStorage.getItem('wrapper_token')",
                key="ls_token",
            )
            email = streamlit_js_eval(
                js_expressions="window.localStorage.getItem('wrapper_email')",
                key="ls_email",
            )
        except Exception:
            token = None
        if not token:
            token = get_auth_token()
            email = get_auth_email()
        if token:
            st.session_state.token = token
            if email:
                st.session_state.email = email

    if "token" in st.session_state:
        # Chequeo periódico de inactividad
        st_autorefresh(interval=60_000, key="auth_refresh")
        _check_inactividad()
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
                    _clear_auth_state()
            except Exception:
                pass

    if ENV == "dev":
        st.write("DEBUG token in session:", "token" in st.session_state)
        st.write("DEBUG token from cookies:", get_auth_token())


def logout_button() -> None:
    if st.session_state.get("token") and st.sidebar.button("Cerrar sesión"):
        _clear_auth_state(rerun=True)
