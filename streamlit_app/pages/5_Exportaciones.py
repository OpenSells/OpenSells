import streamlit as st

import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.components.sidebar_plan import render_sidebar_plan

st.set_page_config(page_title="Exportaciones", page_icon="📤")

PAGE_NAME = "Exportaciones"
remember_current_page(PAGE_NAME)
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

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

render_sidebar_plan(http_client)

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
