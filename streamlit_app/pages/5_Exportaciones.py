import streamlit as st

from streamlit_app.utils.auth_utils import (
    rehydrate_session,
    clear_session,
    get_token,
    get_user,
)
from streamlit_app.utils.auth_guard import require_auth_or_render_home_login
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Exportaciones", page_icon="📤")

rehydrate_session()
if not require_auth_or_render_home_login():
    st.stop()
st.session_state["last_path"] = "pages/5_Exportaciones.py"
token = get_token()
user = get_user()

if st.sidebar.button("Cerrar sesión"):
    clear_session()
    st.rerun()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
