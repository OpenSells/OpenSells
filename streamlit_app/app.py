"""Main entry point for the Streamlit app."""

import streamlit as st

from sidebar_utils import global_reset_button
from auth_utils import ensure_token_and_user, logout_button

st.set_page_config(page_title="Wrapper Leads SaaS", page_icon="🕵️‍♂️")
global_reset_button()
logout_button()
ensure_token_and_user()
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
