"""Main entry point for the Streamlit app."""

import streamlit as st

from sidebar_utils import global_reset_button
from utils.cancel_page import show_cancel_page
from utils.success_page import show_success_page

query_params = st.experimental_get_query_params()
if "page" in query_params:
    if query_params["page"][0] == "success":
        show_success_page()
        st.stop()
    if query_params["page"][0] == "cancel":
        show_cancel_page()
        st.stop()

st.set_page_config(page_title="Wrapper Leads SaaS", page_icon="🕵️‍♂️")
global_reset_button()
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
