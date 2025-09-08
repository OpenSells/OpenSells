import os
import requests
from typing import Any, Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .auth_session import get_auth_token

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _full_url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _build_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        allowed_methods=frozenset({"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}),
        status_forcelist=[502, 503, 504, 520, 521, 522, 523, 524, 525, 526],
        raise_on_status=False,
        raise_on_redirect=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "WrapperLeads/1.0"})
    return s


_session = _build_session()


def _reset_session() -> None:
    global _session
    try:
        _session.close()
    except Exception:
        pass
    _session = _build_session()


DEFAULT_TIMEOUT = (3.05, 15)  # (connect, read)


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
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    url = _full_url(path)
    try:
        r = _session.get(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    except (requests.ConnectionError, requests.ChunkedEncodingError):
        _reset_session()
        hdrs = _merge_headers({**(custom_headers or {}), "Connection": "close"})
        r = _session.get(url, headers=hdrs, timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def post(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    url = _full_url(path)
    try:
        r = _session.post(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    except (requests.ConnectionError, requests.ChunkedEncodingError):
        _reset_session()
        hdrs = _merge_headers({**(custom_headers or {}), "Connection": "close"})
        r = _session.post(url, headers=hdrs, timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def put(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    url = _full_url(path)
    try:
        r = _session.put(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    except (requests.ConnectionError, requests.ChunkedEncodingError):
        _reset_session()
        hdrs = _merge_headers({**(custom_headers or {}), "Connection": "close"})
        r = _session.put(url, headers=hdrs, timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def delete(path: str, **kwargs):
    custom_headers = kwargs.pop("headers", None)
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    url = _full_url(path)
    try:
        r = _session.delete(url, headers=_merge_headers(custom_headers), timeout=timeout, **kwargs)
    except (requests.ConnectionError, requests.ChunkedEncodingError):
        _reset_session()
        hdrs = _merge_headers({**(custom_headers or {}), "Connection": "close"})
        r = _session.delete(url, headers=hdrs, timeout=timeout, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r
