import streamlit as st

from session_bootstrap import bootstrap
bootstrap()

from plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from auth_utils import ensure_token_and_user, logout_button

st.set_page_config(page_title="Emails", page_icon="✉️")
logout_button()
ensure_token_and_user()

if "token" not in st.session_state:
    st.error("Debes iniciar sesión para ver esta página.")
    st.stop()

plan = obtener_plan(st.session_state.token)

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
