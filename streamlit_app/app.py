# streamlit_app/app.py
import streamlit as st

st.set_page_config(page_title="Wrapper Leads SaaS", page_icon="🕵️‍♂️")

_CSS = """
<style>
    .stButton>button {padding:0.6rem 1rem;border-radius:6px;font-weight:600;}
    .block-container {padding-top:2rem;}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

st.title("🧠 Wrapper Leads SaaS")
st.markdown(
    """
Bienvenido a tu plataforma de extracción y gestión de leads.
Usa el menú lateral para acceder a las siguientes funciones:

- Buscar leads y extraer datos automáticamente.
- Gestionar tus nichos y leads guardados.
- Ver tareas pendientes.
- Configurar tu cuenta y estadísticas.
"""
)
