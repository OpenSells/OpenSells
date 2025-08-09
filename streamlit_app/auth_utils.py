import os, streamlit as st
import requests
from dotenv import load_dotenv
from cache_utils import limpiar_cache
from cookies_utils import get_cm, clear_auth_cookies

load_dotenv()
BACKEND_URL = (
    st.secrets.get("BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or "https://opensells.onrender.com"
)


def ensure_token_and_user() -> None:
    if "token" not in st.session_state:
        cm = get_cm()
        token = cm.get("wrapper_token")
        if token:
            st.session_state.token = token
            email = cm.get("wrapper_email")
            if email:
                st.session_state.email = email

    if "token" in st.session_state:
        if st.session_state.get("logout_flag"):
            del st.session_state["logout_flag"]

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


def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión"):
        limpiar_cache()
        clear_auth_cookies()
        st.session_state.clear()
        st.session_state.logout_flag = True
        st.rerun()
