import streamlit as st

from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.utils.auth_utils import ensure_session_or_redirect, clear_session
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

st.set_page_config(page_title="Emails", page_icon="✉️")


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
