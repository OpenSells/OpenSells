import streamlit as st

from streamlit_app.utils.auth_utils import ensure_session_or_redirect, clear_session
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Exportaciones", page_icon="📤")


ensure_session_or_redirect("Home")
token = st.session_state.get("auth_token")
user = st.session_state.get("user")
if not user:
    resp_user = http_client.get("/me")
    if resp_user is not None and resp_user.status_code == 200:
        user = resp_user.json()
        st.session_state["user"] = user

if st.sidebar.button("Cerrar sesión"):
    clear_session(preserve_logout_flag=True)
    st.query_params.clear()
    st.switch_page("Home")

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
