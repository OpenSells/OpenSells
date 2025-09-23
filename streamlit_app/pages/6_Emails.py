import streamlit as st

from streamlit_app.plan_utils import resolve_user_plan, tiene_suscripcion_activa, subscription_cta
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button
from components.ui import render_whatsapp_fab

st.set_page_config(page_title="Emails", page_icon="✉️")

PAGE_NAME = "Emails"
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
