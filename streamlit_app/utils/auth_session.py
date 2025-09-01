import base64
import streamlit as st

TOKEN_KEY = "auth_token"

def _encode(v: str) -> str:
    return base64.urlsafe_b64encode(v.encode()).decode()


def _decode(v: str) -> str:
    return base64.urlsafe_b64decode(v.encode()).decode()


def set_auth_token(token: str):
    st.session_state[TOKEN_KEY] = token
    qp = st.query_params
    qp["t"] = _encode(token)
    st.query_params = qp


def clear_auth_token():
    if TOKEN_KEY in st.session_state:
        del st.session_state[TOKEN_KEY]
    qp = st.query_params
    if "t" in qp:
        del qp["t"]
    st.query_params = qp


def get_auth_token() -> str | None:
    if TOKEN_KEY in st.session_state:
        return st.session_state[TOKEN_KEY]
    t = st.query_params.get("t")
    if t:
        try:
            tok = _decode(t)
            st.session_state[TOKEN_KEY] = tok
            return tok
        except Exception:
            pass
    return None


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


def is_authenticated() -> bool:
    return get_auth_token() is not None
