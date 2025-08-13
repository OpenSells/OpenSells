import streamlit as st

from streamlit_app.plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from streamlit_app.auth_utils import ensure_token_and_user, logout_button
from streamlit_app.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Emails", page_icon="✉️")


def api_me(token: str):
    return http_client.get("/me", headers={"Authorization": f"Bearer {token}"})


user, token = ensure_token_and_user(api_me)
if user is None or token is None:
    st.error("No se pudo validar la sesión. Inicia sesión de nuevo.")
    st.stop()

logout_button()

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
