import streamlit as st

from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.utils.auth_utils import ensure_session, logout_button
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Emails", page_icon="✉️")


user, token = ensure_session(require_auth=True)

logout_button()

plan = (user or {}).get("plan", "free")

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
