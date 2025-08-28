import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from .nav import go, HOME_PAGE

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


def _clear_auth_cookies():
    streamlit_js_eval(js='document.cookie="token=; Max-Age=0; path=/";', key="ck_token")
    streamlit_js_eval(js='document.cookie="Authorization=; Max-Age=0; path=/";', key="ck_auth")


def save_session(token: str, email: str):
    st.session_state["auth_token"] = token
    st.session_state["auth_email"] = email
    _ls_set(LS_TOKEN_KEY, token)
    _ls_set(LS_EMAIL_KEY, email)
    _ls_rm(LS_LOGOUT_FLAG)


def is_authenticated() -> bool:
    return bool(st.session_state.get("auth_token")) and bool(st.session_state.get("auth_email"))


def restore_session_if_allowed() -> bool:
    if _ls_get(LS_LOGOUT_FLAG):
        return False
    if st.session_state.get(RESTORE_FLAG):
        return is_authenticated()
    st.session_state[RESTORE_FLAG] = True
    if is_authenticated():
        return True
    tok = _ls_get(LS_TOKEN_KEY)
    eml = _ls_get(LS_EMAIL_KEY)
    if tok and eml:
        st.session_state["auth_token"] = tok
        st.session_state["auth_email"] = eml
        st.rerun()
        return True
    return False


def clear_session(preserve_logout_flag: bool = True):
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_email", None)
    st.session_state.pop(RESTORE_FLAG, None)
    _ls_rm(LS_TOKEN_KEY)
    _ls_rm(LS_EMAIL_KEY)
    if preserve_logout_flag:
        _ls_set(LS_LOGOUT_FLAG, "1")
    else:
        _ls_rm(LS_LOGOUT_FLAG)
    _clear_auth_cookies()


def ensure_session_or_redirect(home_page: str = HOME_PAGE):
    if not is_authenticated():
        restore_session_if_allowed()
    if not is_authenticated():
        go(home_page, clear_query=True)
