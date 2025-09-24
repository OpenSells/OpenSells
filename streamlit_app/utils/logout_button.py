import streamlit as st

from streamlit_app.auth_client import clear_token
from .auth_session import clear_page_remember
from .nav import go


def logout_button():
    if st.button("Cerrar sesión", type="secondary"):
        clear_token()
        clear_page_remember()
        go("Home.py")
        st.rerun()
