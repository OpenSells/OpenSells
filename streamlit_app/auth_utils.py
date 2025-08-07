import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from streamlit_js_eval import get_cookie, set_cookie

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")


def set_token_cookie(token: str) -> None:
    set_cookie("wrapper_token", token, 7)


def ensure_token_and_user() -> None:
    if "token" not in st.session_state and not st.session_state.get("logout_flag"):
        token = get_cookie("wrapper_token")
        if token:
            st.session_state.token = token

    if "token" in st.session_state:
        set_token_cookie(st.session_state.token)
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
        components.html(
            """
            <script>
            document.cookie = 'wrapper_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
            </script>
            """,
            height=0,
        )
        st.session_state.clear()
        st.session_state.logout_flag = True
        st.rerun()
