import time
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from cache_utils import limpiar_cache
from cookies_utils import clear_auth_cookies

TIMEOUT_MINUTES = 20  # Tiempo de inactividad permitido


def _ls_get(key: str):
    """Leer un valor de localStorage."""
    try:
        return streamlit_js_eval(
            js_expressions=f"window.localStorage.getItem('{key}')",
            key=f"get_{key}",
        )
    except Exception:
        return None


def _ls_set(key: str, value: str) -> None:
    """Guardar un valor en localStorage."""
    try:
        streamlit_js_eval(
            js_expressions=f"window.localStorage.setItem('{key}', '{value}')",
            key=f"set_{key}",
        )
    except Exception:
        pass


def _ls_remove(key: str) -> None:
    """Eliminar una clave de localStorage."""
    try:
        streamlit_js_eval(
            js_expressions=f"window.localStorage.removeItem('{key}')",
            key=f"rm_{key}",
        )
    except Exception:
        pass


def record_activity_js() -> None:
    """Registra actividad del usuario en localStorage.lastActivity."""
    try:
        streamlit_js_eval(
            js_expressions="""
            (() => {
                const key = 'lastActivity';
                const update = () => localStorage.setItem(key, Date.now());
                ['mousemove','keydown','click','scroll','touchstart'].forEach(
                    e => document.addEventListener(e, update)
                );
                if (!localStorage.getItem(key)) update();
            })();
            """,
            key="rec_activity",
        )
    except Exception:
        pass


def save_token(token: str) -> None:
    """Persistir token en sesión y localStorage."""
    st.session_state.token = token
    _ls_set("wrapper_token", token)
    _ls_set("lastActivity", str(int(time.time() * 1000)))
    # TODO(Ayrton): mover a refresh tokens con cookies HttpOnly


def logout(silent: bool = False) -> None:
    """Eliminar toda la información de autenticación."""
    limpiar_cache()
    clear_auth_cookies()
    _ls_remove("wrapper_token")
    _ls_remove("lastActivity")
    st.session_state.clear()
    if not silent:
        st.experimental_set_query_params()
        st.rerun()


def ensure_token_and_user(fetch_me_fn):
    """Asegura token y usuario en sesión."""
    record_activity_js()
    token = st.session_state.get("token") or _ls_get("wrapper_token")
    if token:
        st.session_state.token = token
        last = _ls_get("lastActivity")
        if last:
            now_ms = int(time.time() * 1000)
            if now_ms - int(last) > TIMEOUT_MINUTES * 60 * 1000:
                logout(silent=True)
                st.rerun()
        if "user" not in st.session_state:
            try:
                resp = fetch_me_fn(token)
                if resp.status_code == 200:
                    st.session_state.user = resp.json()
                else:
                    logout(silent=True)
                    st.rerun()
            except Exception:
                pass
        return st.session_state.get("user"), token
    return None, None


def logout_button(label: str = "Cerrar sesión") -> None:
    """Renderiza un botón de cierre de sesión en el sidebar."""
    if st.session_state.get("token") and st.sidebar.button(label):
        logout()
