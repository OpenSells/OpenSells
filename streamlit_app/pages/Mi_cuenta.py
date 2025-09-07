import streamlit as st
from streamlit_app.utils.auth_utils import get_session, get_profile

st.set_page_config(page_title="Mi cuenta", page_icon="👤", layout="centered")

if not get_session():
    st.warning("Inicia sesión para ver tu cuenta.")
    st.page_link("Home.py", label="Volver a Home", icon="↩️")
    st.stop()

st.title("Mi cuenta")

profile = get_profile() or {}
username = profile.get("username") or "—"
email = profile.get("email") or "—"

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Usuario", value=username)
with col2:
    st.metric(label="Email", value=email)

st.caption("Pronto podrás editar tus datos y preferencias desde aquí.")
