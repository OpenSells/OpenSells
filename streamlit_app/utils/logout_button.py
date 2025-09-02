import streamlit as st
from .auth_session import clear_auth_token, clear_page_remember


def logout_button():
    if st.button("Cerrar sesión", type="secondary"):
        clear_auth_token()
        clear_page_remember()
        st.switch_page("Home.py")
