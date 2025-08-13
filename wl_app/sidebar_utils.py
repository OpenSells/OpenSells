import streamlit as st

from wl_app.cache_utils import limpiar_cache

def global_reset_button():
    """Render a sidebar button to clear cache and rerun the app."""
    if st.sidebar.button("Reiniciar cache"):
        limpiar_cache()
        st.rerun()
