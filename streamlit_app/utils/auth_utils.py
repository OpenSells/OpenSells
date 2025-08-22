import os
import os
import streamlit as st


def get_backend_url() -> str:
    # 1) ENV primero
    env = os.getenv("BACKEND_URL")
    if env:
        return env.rstrip("/")

    # 2) st.secrets si existe, sin romper si no hay secrets.toml
    try:
        val = st.secrets.get("BACKEND_URL", None)
        if val:
            return str(val).rstrip("/")
    except Exception:
        pass

    # 3) Fallback
    return "http://localhost:8000"


def ensure_session(require_auth: bool = False):
    """
    Devuelve (user, token). Si require_auth=True y no hay token, muestra aviso y corta la ejecución.
    """
    user = st.session_state.get("user")
    token = st.session_state.get("token")
    if require_auth and not token:
        st.error("Tu sesión no está activa. Inicia sesión en Home.")
        try:
            st.switch_page("Home.py")
        except Exception:
            st.stop()
    return user, token


def logout_and_redirect():
    st.session_state.pop("user", None)
    st.session_state.pop("token", None)
    st.success("Sesión cerrada correctamente.")
    try:
        st.switch_page("Home.py")
    except Exception:
        st.stop()


def handle_401_and_redirect():
    st.warning("Sesión expirada o inválida. Vuelve a iniciar sesión.")
    logout_and_redirect()

