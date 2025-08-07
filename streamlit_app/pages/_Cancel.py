import streamlit as st
from auth_utils import ensure_token_and_user

st.set_page_config(
    page_title="❌ Suscripción cancelada",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ensure_token_and_user()

st.title("❌ Suscripción cancelada")
st.warning(
    "El proceso de pago no se ha completado. Puedes volver a intentarlo desde tu cuenta."
)

if st.button("👤 Volver a Mi Cuenta"):
    st.switch_page("pages/4_Mi_Cuenta.py")

