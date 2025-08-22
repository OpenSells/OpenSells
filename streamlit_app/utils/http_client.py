import requests
import streamlit as st
from .auth_utils import get_backend_url, handle_401_and_redirect

BACKEND_URL = get_backend_url()


def _session_with_auth():
    s = requests.Session()
    token = st.session_state.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    s.headers.update({"Accept": "application/json"})
    return s


def api_get(path: str, **kwargs) -> requests.Response:
    url = f"{BACKEND_URL}/{path.lstrip('/')}"
    with _session_with_auth() as s:
        resp = s.get(url, timeout=30, **kwargs)
    if resp.status_code == 401:
        handle_401_and_redirect()
    return resp


def api_post(path: str, json=None, data=None, params=None, **kwargs) -> requests.Response:
    url = f"{BACKEND_URL}/{path.lstrip('/')}"
    with _session_with_auth() as s:
        resp = s.post(url, json=json, data=data, params=params, timeout=30, **kwargs)
    if resp.status_code == 401:
        handle_401_and_redirect()
    return resp


def api_delete(path: str, params=None, **kwargs) -> requests.Response:
    url = f"{BACKEND_URL}/{path.lstrip('/')}"
    with _session_with_auth() as s:
        resp = s.delete(url, params=params, timeout=30, **kwargs)
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
