"""Helpers to guard pages that require authentication."""

from __future__ import annotations

import streamlit as st

from .auth_utils import is_authenticated
from .nav import HOME_PAGE


def require_auth_or_render_home_login() -> bool:
    """Ensure the user is authenticated or render a login hint."""
    if is_authenticated():
        return True

    st.info("Necesitas iniciar sesión")
    try:
        st.page_link(HOME_PAGE, label="Ir a Home")
    except AttributeError:
        st.link_button("Ir a Home", HOME_PAGE)
    return False

