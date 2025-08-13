import streamlit as st

from wl_app.cookies_utils import init_cookie_manager_mount

def bootstrap() -> None:
    """Initialise components that must run before any auth checks."""
    init_cookie_manager_mount()
    st.session_state.setdefault("_bootstrapped", True)
