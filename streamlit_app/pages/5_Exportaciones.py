import streamlit as st

from streamlit_app.auth_utils import get_session_user, logout_button
from streamlit_app.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Exportaciones", page_icon="📤")


token, user = get_session_user(require_auth=True)

logout_button()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
