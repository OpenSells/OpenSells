import streamlit as st
from .auth_session import is_authenticated, remember_current_page


def ensure_session_or_access(page_name: str):
    remember_current_page(page_name)
    if not is_authenticated():
        st.title("Acceder")
        st.info("Inicia sesión para continuar.")
        st.stop()
