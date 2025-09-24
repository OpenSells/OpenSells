import os
from typing import Optional

import requests
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LS_KEY = "wrapper_jwt"


def _ls_get_token() -> Optional[str]:
    token = streamlit_js_eval(js_expressions="localStorage.getItem('%s')" % LS_KEY, key="get_jwt")
    if token and isinstance(token, str):
        token = token.strip()
        if token:
            return token
    return None


def _ls_set_token(token: str) -> None:
    safe = token.replace("\\", "\\\\").replace("'", "\\'")
    streamlit_js_eval(js_expressions=f"localStorage.setItem('{LS_KEY}', '{safe}')", key="set_jwt")


def _ls_clear_token() -> None:
    streamlit_js_eval(js_expressions=f"localStorage.removeItem('{LS_KEY}')", key="del_jwt")


def save_token(token: str) -> None:
    st.session_state["jwt"] = token
    st.session_state["auth_token"] = token
    _ls_set_token(token)


def clear_token() -> None:
    st.session_state.pop("jwt", None)
    st.session_state.pop("auth_token", None)
    st.session_state.pop("me", None)
    st.session_state.pop("auth_email", None)
    _ls_clear_token()


def current_token() -> Optional[str]:
    token = st.session_state.get("jwt") or st.session_state.get("auth_token")
    if token:
        st.session_state["jwt"] = token
        st.session_state["auth_token"] = token
        return token
    token = _ls_get_token()
    if token:
        st.session_state["jwt"] = token
        st.session_state["auth_token"] = token
        return token
    return None


def fetch_me(token: str) -> Optional[dict]:
    try:
        r = requests.get(
            f"{BACKEND_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def ensure_authenticated() -> bool:
    token = current_token()
    if not token:
        return False
    me = fetch_me(token)
    if not me:
        clear_token()
        return False
    st.session_state["me"] = me
    st.session_state["user"] = me
    return True


def auth_headers() -> dict:
    token = current_token()
    return {"Authorization": f"Bearer {token}"} if token else {}
