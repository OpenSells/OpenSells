"""Authentication session helpers with persistence and rehydration."""

from __future__ import annotations

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from .cookies_utils import init_cookie_manager_mount, set_auth_token, get_auth_token, clear_auth_token


LS_TOKEN_KEY = "auth_token"
RESTORE_FLAG = "_auth_restored"


def _ls_get(key: str) -> str | None:
    return streamlit_js_eval(js=f'localStorage.getItem("{key}")', key=f"get_{key}") or None


def _ls_set(key: str, val: str) -> None:
    streamlit_js_eval(js=f'localStorage.setItem("{key}", {val!r})', key=f"set_{key}")


def _ls_rm(key: str) -> None:
    streamlit_js_eval(js=f'localStorage.removeItem("{key}")', key=f"rm_{key}")


def set_session(token: str, user: dict | None = None) -> None:
    """Persist the auth token (and optional user) in session and storage."""
    st.session_state["auth_token"] = token
    if user is not None:
        st.session_state["user"] = user
    _ls_set(LS_TOKEN_KEY, token)
    set_auth_token(token)


def get_token() -> str | None:
    return st.session_state.get("auth_token")


def get_user() -> dict | None:
    return st.session_state.get("user")


def is_authenticated() -> bool:
    return bool(get_token())


def clear_session() -> None:
    """Remove token and user info from all stores."""
    st.session_state.pop("auth_token", None)
    st.session_state.pop("user", None)
    st.session_state.pop(RESTORE_FLAG, None)
    st.session_state.pop("_handling_401", None)
    _ls_rm(LS_TOKEN_KEY)
    clear_auth_token()


def rehydrate_session() -> None:
    """Restore auth information from storage into session_state if needed."""
    if st.session_state.get(RESTORE_FLAG):
        return
    st.session_state[RESTORE_FLAG] = True

    if get_token():
        return

    token = _ls_get(LS_TOKEN_KEY) or get_auth_token()
    if token:
        st.session_state["auth_token"] = token
        set_auth_token(token)
        if not get_user():
            try:
                from streamlit_app.utils import http_client

                resp = http_client.get("/me")
                if getattr(resp, "status_code", None) == 200:
                    st.session_state["user"] = resp.json()
            except Exception:
                pass


# Initialize cookie manager early
init_cookie_manager_mount()

