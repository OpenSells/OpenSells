import requests
import streamlit as st

from .auth_utils import get_backend_url, handle_401_and_redirect


def _session_with_auth():
    s = requests.Session()
    token = st.session_state.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    s.headers.update({"Accept": "application/json"})
    return s


def _url(path: str) -> str:
    return f"{get_backend_url()}/{path.lstrip('/')}"


def api_get(path: str, **kwargs) -> requests.Response:
    with _session_with_auth() as s:
        resp = s.get(_url(path), timeout=30, **kwargs)
    if resp.status_code == 401:
        handle_401_and_redirect()
    return resp


def api_post(path: str, json=None, data=None, params=None, **kwargs) -> requests.Response:
    with _session_with_auth() as s:
        resp = s.post(_url(path), json=json, data=data, params=params, timeout=30, **kwargs)
    if resp.status_code == 401:
        handle_401_and_redirect()
    return resp


def api_delete(path: str, params=None, **kwargs) -> requests.Response:
    with _session_with_auth() as s:
        resp = s.delete(_url(path), params=params, timeout=30, **kwargs)
    if resp.status_code == 401:
        handle_401_and_redirect()
    return resp


# Backwards compatibility
get = api_get
post = api_post
delete = api_delete


def health_ok() -> bool:
    try:
        r = api_get("/health")
        if r.status_code < 500:
            return True
    except Exception:
        pass
    try:
        r = api_get("/")
        return r.status_code < 500
    except Exception:
        return False

