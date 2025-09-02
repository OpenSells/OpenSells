import base64
import streamlit as st

# 👇 🔵 NEW: import conditional for extra_streamlit_components
try:
    import extra_streamlit_components as stx
except Exception:  # pragma: no cover
    stx = None

TOKEN_KEY = "auth_token"
_LS_KEY = "wrapper_auth_b64"


def _encode(v: str) -> str:
    return base64.urlsafe_b64encode(v.encode()).decode()


def _decode(v: str) -> str:
    return base64.urlsafe_b64decode(v.encode()).decode()


def _localstorage_set(b64: str | None):
    if stx is None:
        return
    try:
        stx.LocalStorage().set_item(_LS_KEY, b64 if b64 is not None else "")
    except Exception:
        pass


def _localstorage_get() -> str | None:
    if stx is None:
        return None
    try:
        val = stx.LocalStorage().get_item(_LS_KEY)
        if not val:
            return None
        return val
    except Exception:
        return None


def set_auth_token(token: str):
    # State in memory
    st.session_state[TOKEN_KEY] = token
    # URL
    qp = st.query_params
    qp["t"] = _encode(token)
    st.query_params = qp
    # 👇 NEW: mirror in LocalStorage
    _localstorage_set(_encode(token))


def clear_auth_token():
    # Memory
    if TOKEN_KEY in st.session_state:
        del st.session_state[TOKEN_KEY]
    # URL
    qp = st.query_params
    if "t" in qp:
        del qp["t"]
    st.query_params = qp
    # 👇 NEW: clear LocalStorage
    _localstorage_set(None)


def get_auth_token() -> str | None:
    # 1) memory
    if TOKEN_KEY in st.session_state:
        return st.session_state[TOKEN_KEY]
    # 2) URL
    t = st.query_params.get("t")
    if t:
        try:
            tok = _decode(t)
            st.session_state[TOKEN_KEY] = tok
            # ensure mirror in LocalStorage
            _localstorage_set(_encode(tok))
            return tok
        except Exception:
            pass
    # 3) 👇 NEW: LocalStorage
    b64 = _localstorage_get()
    if b64:
        try:
            tok = _decode(b64)
            st.session_state[TOKEN_KEY] = tok
            # ensure URL for subsequent refreshes
            qp = st.query_params
            if qp.get("t") != b64:
                qp["t"] = b64
                st.query_params = qp
            return tok
        except Exception:
            pass
    return None


def is_authenticated() -> bool:
    return get_auth_token() is not None


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


# 👇 NEW: bootstrap helper
def bootstrap_auth_once():
    """
    Attempts to restore the token from session_state, query params or LocalStorage.
    Should be called at the start of Home.py once per render session.
    """
    flag = "_auth_bootstrapped"
    if st.session_state.get(flag):
        return
    _ = get_auth_token()
    st.session_state[flag] = True
