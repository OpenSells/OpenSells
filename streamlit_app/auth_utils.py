import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from streamlit_js_eval import get_cookie, set_cookie

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")

def set_token_cookie(token: str) -> None:
    set_cookie("wrapper_token", token)

def ensure_token_and_user() -> None:
    if "token" not in st.session_state:
        token = get_cookie("wrapper_token")
        if token:
            st.session_state.token = token
    if "token" in st.session_state:
        set_token_cookie(st.session_state.token)
    if "usuario" not in st.session_state and st.session_state.get("token"):
        try:
            r = requests.get(
                f"{BACKEND_URL}/usuario_actual",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=10,
            )
            if r.status_code == 200:
                st.session_state.usuario = r.json()
        except Exception:
            pass

def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión"):
        components.html(
            """
            <script>
            document.cookie = 'wrapper_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
            </script>
            """,
            height=0,
        )
        st.session_state.clear()
        st.experimental_rerun()
