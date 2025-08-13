import streamlit as st

from streamlit.session_bootstrap import bootstrap
from streamlit.auth_utils import ensure_token_and_user, logout_button
from streamlit.utils import http_client

bootstrap()

st.set_page_config(page_title="Exportaciones", page_icon="📤")


def api_me(token: str):
    return http_client.get("/me", headers={"Authorization": f"Bearer {token}"})


user, token = ensure_token_and_user(api_me)
if user is None or token is None:
    st.error("No se pudo validar la sesión. Inicia sesión de nuevo.")
    st.stop()

logout_button()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
