from __future__ import annotations

from typing import Callable, Optional, Tuple

import streamlit as st


def save_token(token: Optional[str]) -> None:
    """Store token in the current session state."""
    if token:
        st.session_state["token"] = token


def logout_button(label: str = "Cerrar sesión") -> None:
    """Render a logout button in the sidebar that clears the token."""
    if st.sidebar.button(label):
        if "token" in st.session_state:
            del st.session_state["token"]
        st.rerun()


def ensure_token_and_user(
    api_me: Callable[[str], dict | None]
) -> Tuple[dict | None, str | None]:
    """Return user and token if a valid session exists.

    The token is read from ``st.session_state``. If present, ``api_me`` is called
    with the token to retrieve user information. Any error or missing data
    results in ``(None, None)`` without raising exceptions.
    """
    token = st.session_state.get("token")
    if not token:
        return None, None
    try:
        user = api_me(token)
    except Exception:
        return None, None
    if not user:
        return None, None
    return user, token
