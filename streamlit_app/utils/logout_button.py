import streamlit as st
from .auth_session import clear_auth_token, clear_page_remember
from .nav import go


def logout_button():
    if st.button("Cerrar sesión", type="secondary"):
        clear_auth_token()
        clear_page_remember()
        go("Home.py")
