import streamlit as st

from streamlit_app.utils import http_client
from streamlit_app.utils.guards import ensure_session_or_access
from streamlit_app.utils.auth_session import remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button

st.set_page_config(page_title="Exportaciones", page_icon="📤")

PAGE_NAME = "Exportaciones"
ensure_session_or_access(PAGE_NAME)
remember_current_page(PAGE_NAME)

token = get_auth_token()
user = st.session_state.get("user")
if token and not user:
    resp_user = http_client.get("/me")
    if isinstance(resp_user, dict) and resp_user.get("_error") == "unauthorized":
        st.warning("Sesión expirada. Vuelve a iniciar sesión.")
        st.stop()
    if getattr(resp_user, "status_code", None) == 200:
        user = resp_user.json()
        st.session_state["user"] = user

with st.sidebar:
    logout_button()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
