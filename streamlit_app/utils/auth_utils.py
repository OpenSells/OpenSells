import streamlit as st
from typing import Tuple, Optional
from streamlit_js_eval import streamlit_js_eval
from streamlit_app.utils import http_client
from streamlit_app.utils.cookies_utils import (
    get_auth_token,
    set_auth_token,
    clear_auth_token,
)

LS_TOKEN_KEY = "wrapper_auth_token"
LS_EMAIL_KEY = "wrapper_auth_email"
LS_LOGOUT_FLAG = "wrapper_logged_out"


def save_session(token: str, email: str):
    """Persist credentials in session_state and localStorage."""
    st.session_state["auth_token"] = token
    st.session_state["auth_email"] = email
    # backward compat keys
    st.session_state["token"] = token
    st.session_state["email"] = email

    streamlit_js_eval(js=f'localStorage.setItem("{LS_TOKEN_KEY}", {token!r});', key="js_set_token")
    streamlit_js_eval(js=f'localStorage.setItem("{LS_EMAIL_KEY}", {email!r});', key="js_set_email")
    streamlit_js_eval(js=f'localStorage.removeItem("{LS_LOGOUT_FLAG}");', key="js_del_logout_flag")
    try:
        set_auth_token(token)
    except Exception:
        pass


def restore_session_if_allowed() -> bool:
    """Load credentials from session_state or localStorage unless logout flag exists."""
    logout_flag = streamlit_js_eval(js=f'localStorage.getItem("{LS_LOGOUT_FLAG}");', key="js_get_logout_flag") or ""
    if logout_flag:
        return False

    token = st.session_state.get("auth_token") or st.session_state.get("token")
    email = st.session_state.get("auth_email") or st.session_state.get("email")
    if token and email:
        st.session_state["auth_token"] = token
        st.session_state["token"] = token
        st.session_state["auth_email"] = email
        st.session_state["email"] = email
        return True

    token = streamlit_js_eval(js=f'localStorage.getItem("{LS_TOKEN_KEY}");', key="js_get_token") or ""
    email = streamlit_js_eval(js=f'localStorage.getItem("{LS_EMAIL_KEY}");', key="js_get_email") or ""
    if token and email:
        st.session_state["auth_token"] = token
        st.session_state["token"] = token
        st.session_state["auth_email"] = email
        st.session_state["email"] = email
        return True

    # fallback to legacy cookie if present
    token = get_auth_token()
    if token:
        st.session_state["auth_token"] = token
        st.session_state["token"] = token
        return True

    return False


def clear_session(preserve_logout_flag: bool = True):
    """Clear credentials from session_state and storage."""
    for k in ("auth_token", "auth_email", "token", "email", "user", "csv_bytes", "csv_filename", "lead_actual"):
        st.session_state.pop(k, None)
    streamlit_js_eval(js=f'localStorage.removeItem("{LS_TOKEN_KEY}");', key="js_rm_token")
    streamlit_js_eval(js=f'localStorage.removeItem("{LS_EMAIL_KEY}");', key="js_rm_email")
    if preserve_logout_flag:
        streamlit_js_eval(js=f'localStorage.setItem("{LS_LOGOUT_FLAG}", "1");', key="js_set_logout_flag")
    else:
        streamlit_js_eval(js=f'localStorage.removeItem("{LS_LOGOUT_FLAG}");', key="js_rm_logout_flag")
    try:
        clear_auth_token()
    except Exception:
        pass


def is_authenticated() -> bool:
    return bool(st.session_state.get("auth_token")) and bool(st.session_state.get("auth_email"))


def ensure_session() -> Tuple[Optional[dict], Optional[str]]:
    """Return (user, token) ensuring valid session or None."""
    if not restore_session_if_allowed():
        return None, None
    token = st.session_state.get("auth_token")
    if not token:
        return None, None

    resp = http_client.get("/me")
    if getattr(resp, "status_code", None) == 200:
        user = resp.json()
        st.session_state["user"] = user
        set_auth_token(token)
        return user, token

    clear_session(preserve_logout_flag=False)
    return None, None


def require_auth_or_prompt() -> bool:
    if not is_authenticated():
        restore_session_if_allowed()
    if not is_authenticated():
        st.info("Inicia sesión para obtener acceso.")
        return False
    return True


def logout_and_redirect(target: str = "Home.py"):
    clear_session(preserve_logout_flag=True)
    try:
        st.switch_page(target)
    except Exception:
        st.rerun()
