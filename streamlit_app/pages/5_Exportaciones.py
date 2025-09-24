import streamlit as st

from streamlit_app.auth_client import ensure_authenticated, current_token
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.auth_session import remember_current_page
from streamlit_app.utils.logout_button import logout_button
from components.ui import render_whatsapp_fab

st.set_page_config(page_title="Exportaciones", page_icon="📤")

PAGE_NAME = "Exportaciones"
remember_current_page(PAGE_NAME)
if not ensure_authenticated():
    st.title(PAGE_NAME)
    st.warning("Sesión expirada. Vuelve a iniciar sesión.")
    st.stop()

token = current_token()
user = st.session_state.get("user") or st.session_state.get("me")
if user:
    st.session_state["user"] = user

with st.sidebar:
    logout_button()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")
