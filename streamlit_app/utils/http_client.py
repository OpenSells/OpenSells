import os
import requests
from typing import Any, Dict, Optional
from .auth_session import get_auth_token

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_session = requests.Session()


def _base_headers() -> Dict[str, str]:
    h: Dict[str, str] = {"Accept": "application/json"}
    tok = get_auth_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _merge_headers(custom: Optional[Dict[str, str]]) -> Dict[str, str]:
    base = _base_headers()
    if not custom:
        return base
    base.update(custom)
    return base


def _extract_token(resp: requests.Response) -> Optional[str]:
    token: Optional[str] = None
    try:
        data = resp.json()
    except Exception:
        data = None
    if isinstance(data, dict):
        token = (
            data.get("access_token")
            or data.get("token")
            or (data.get("data") or {}).get("access_token")
            or (data.get("data") or {}).get("token")
        )
    if not token:
        for key in ("access_token", "jwt", "session"):
            if key in resp.cookies:
                token = resp.cookies.get(key)
                break
    return token


def login(username: str, password: str) -> Dict[str, Any]:
    """Attempt to authenticate and return token and raw response."""
    url = f"{BASE_URL}/login"
    resp = _session.post(
        url,
        data={"username": username, "password": password},
        headers=_base_headers(),
        timeout=60,
    )
    token = _extract_token(resp)
    if (not token or resp.status_code >= 400) and resp.status_code != 401:
        resp = _session.post(
            url,
            json={"username": username, "password": password},
            headers=_base_headers(),
            timeout=60,
        )
        token = _extract_token(resp)
    if resp.status_code == 401:
        return {"_error": "unauthorized"}
    return {"response": resp, "token": token}


def get(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", 30)
    url = f"{BASE_URL}{path}"
    r = _session.get(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def post(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", 60)
    url = f"{BASE_URL}{path}"
    r = _session.post(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def put(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", 60)
    url = f"{BASE_URL}{path}"
    r = _session.put(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def delete(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", 30)
    url = f"{BASE_URL}{path}"
    r = _session.delete(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r
