import streamlit as st
from cache_utils import limpiar_cache

def global_reset_button():
    """Render a sidebar button to clear cache and rerun the app."""
    if st.sidebar.button("\ud83d\udd04 Reiniciar cach\xe9"):
        limpiar_cache()
        st.rerun()
