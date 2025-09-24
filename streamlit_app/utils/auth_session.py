"""Backwards-compatible helpers around the new auth_client utilities."""

from __future__ import annotations

import streamlit as st

from auth_client import (
    clear_token as _clear_token,
    current_token as _current_token,
    ensure_authenticated as _ensure_authenticated,
    save_token as _save_token,
)

TOKEN_KEY = "jwt"


def set_auth_token(token: str):
    """Persist the token using the shared auth_client helpers."""
    if not token:
        return
    _save_token(token)


def clear_auth_token():
    """Clear any persisted authentication information."""
    _clear_token()


def get_auth_token() -> str | None:
    """Return the current token, loading it from LocalStorage if needed."""
    return _current_token()


def is_authenticated() -> bool:
    """Check whether a valid token + profile exist in the session."""
    if not _ensure_authenticated():
        return False
    return _current_token() is not None


def remember_current_page(page_name: str):
    qp = st.query_params
    if qp.get("p") != page_name:
        qp["p"] = page_name
        st.query_params = qp


def clear_page_remember():
    qp = st.query_params
    if "p" in qp:
        del qp["p"]
    st.query_params = qp


def bootstrap_auth_once():
    flag = "_auth_bootstrapped"
    if st.session_state.get(flag):
        return
    _ensure_authenticated()
    st.session_state[flag] = True


__all__ = [
    "set_auth_token",
    "clear_auth_token",
    "get_auth_token",
    "is_authenticated",
    "remember_current_page",
    "clear_page_remember",
    "bootstrap_auth_once",
]
