import streamlit as st

from streamlit_app.utils.auth_utils import ensure_session, logout_button
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Exportaciones", page_icon="📤")


user, token = ensure_session(require_auth=True)

logout_button()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
