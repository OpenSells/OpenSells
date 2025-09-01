"""Helpers for managing authentication session across pages."""

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from .cookies_utils import (
    clear_auth_token,
    get_auth_token,
    init_cookie_manager_mount,
    set_auth_token,
)
from .nav import go, LOGIN_PAGE


LS_TOKEN_KEY = "wrapper_auth_token"
LS_EMAIL_KEY = "wrapper_auth_email"
LS_LOGOUT_FLAG = "wrapper_logged_out"
RESTORE_FLAG = "_auth_restore_attempted"


def _ls_get(key: str) -> str:
    return streamlit_js_eval(js=f'localStorage.getItem("{key}")', key=f"get_{key}") or ""


def _ls_set(key: str, val: str):
    streamlit_js_eval(js=f'localStorage.setItem("{key}", {val!r})', key=f"set_{key}")


def _ls_rm(key: str):
    streamlit_js_eval(js=f'localStorage.removeItem("{key}")', key=f"rm_{key}")


def _legacy_clear_auth_cookies():
    """Clear possible backend cookies for backwards compatibility."""
    streamlit_js_eval(js='document.cookie="token=; Max-Age=0; path=/";', key="ck_token")
    streamlit_js_eval(js='document.cookie="Authorization=; Max-Age=0; path=/";', key="ck_auth")


class SessionManager:
    """Persist auth token in session_state, localStorage and cookies."""

    def save_session(self, token: str, email: str) -> None:
        st.session_state["auth_token"] = token
        st.session_state["auth_email"] = email
        _ls_set(LS_TOKEN_KEY, token)
        _ls_set(LS_EMAIL_KEY, email)
        _ls_rm(LS_LOGOUT_FLAG)
        set_auth_token(token)

    def is_authenticated(self) -> bool:
        return bool(st.session_state.get("auth_token"))

    def restore(self) -> bool:
        """Rehydrate session_state from storage if allowed."""
        if _ls_get(LS_LOGOUT_FLAG):
            return False
        if st.session_state.get(RESTORE_FLAG):
            return self.is_authenticated()
        st.session_state[RESTORE_FLAG] = True
        if self.is_authenticated():
            return True
        tok = _ls_get(LS_TOKEN_KEY) or get_auth_token()
        eml = _ls_get(LS_EMAIL_KEY)
        if tok:
            st.session_state["auth_token"] = tok
            if eml:
                st.session_state["auth_email"] = eml
            set_auth_token(tok)
            st.rerun()
            return True
        return False

    def clear_session(self, preserve_logout_flag: bool = True) -> None:
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_email", None)
        st.session_state.pop(RESTORE_FLAG, None)
        _ls_rm(LS_TOKEN_KEY)
        _ls_rm(LS_EMAIL_KEY)
        clear_auth_token()
        if preserve_logout_flag:
            _ls_set(LS_LOGOUT_FLAG, "1")
        else:
            _ls_rm(LS_LOGOUT_FLAG)
        _legacy_clear_auth_cookies()

    def ensure_session_or_redirect(self, login_page: str = LOGIN_PAGE) -> None:
        if not self.is_authenticated():
            self.restore()
        if not self.is_authenticated():
            go(login_page, clear_query=True)


session_manager = SessionManager()

# Backwards compatible top-level functions ---------------------------------

def save_session(token: str, email: str) -> None:
    session_manager.save_session(token, email)


def is_authenticated() -> bool:
    return session_manager.is_authenticated()


def restore_session_if_allowed() -> bool:
    return session_manager.restore()


def clear_session(preserve_logout_flag: bool = True) -> None:
    session_manager.clear_session(preserve_logout_flag=preserve_logout_flag)


def ensure_session_or_redirect(login_page: str = LOGIN_PAGE) -> None:
    session_manager.ensure_session_or_redirect(login_page=login_page)


# Ensure CookieManager is initialized early
init_cookie_manager_mount()

