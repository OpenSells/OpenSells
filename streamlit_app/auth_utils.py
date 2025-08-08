import os
import requests
import streamlit as st
from dotenv import load_dotenv
from cache_utils import limpiar_cache

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")


def ensure_token_and_user() -> None:
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
        st.session_state.clear()
        st.session_state.logout_flag = True
        st.rerun()
