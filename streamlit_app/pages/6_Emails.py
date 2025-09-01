import streamlit as st

from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
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

st.set_page_config(page_title="Emails", page_icon="✉️")

rehydrate_session()
if not require_auth_or_render_home_login():
    st.stop()
st.session_state["last_path"] = "pages/6_Emails.py"
token = get_token()
user = get_user()

if st.sidebar.button("Cerrar sesión"):
    clear_session()
    st.rerun()

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
