# utils/navegacion.py

import streamlit as st

def registrar_pagina_actual(nombre: str):
    """
    Guarda el nombre de la página actual en session_state
    para que otras páginas como app.py puedan detectar el cambio.
    """
    st.session_state["_pagina_actual"] = nombre
