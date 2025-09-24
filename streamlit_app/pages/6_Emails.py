import streamlit as st

from streamlit_app.auth_client import ensure_authenticated, current_token
from streamlit_app.plan_utils import resolve_user_plan, tiene_suscripcion_activa, subscription_cta
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.auth_session import remember_current_page
from streamlit_app.utils.logout_button import logout_button
from components.ui import render_whatsapp_fab

st.set_page_config(page_title="Emails", page_icon="✉️")

PAGE_NAME = "Emails"
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

plan = resolve_user_plan(token)["plan"]

st.title("✉️ Emails")
st.info("Funcionalidad de envío de emails — Disponible próximamente.")
st.markdown(
    """
- Envío 1:1
- Envío masivo
- Plantillas reutilizables
- Seguimiento de aperturas y clics
"""
)

if not tiene_suscripcion_activa(plan):
    st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
    subscription_cta()

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")
