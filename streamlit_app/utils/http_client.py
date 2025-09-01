import os
import requests
from .auth_session import get_auth_token

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
session = requests.Session()

_extra_headers: dict[str, str] = {}


def set_extra_headers(headers: dict[str, str] | None):
    global _extra_headers
    _extra_headers = headers or {}


def _headers():
    h = {"Accept": "application/json"}
    if _extra_headers:
        h.update(_extra_headers)
    tok = get_auth_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def get(path: str, **kwargs):
    resp = session.get(f"{BASE_URL}{path}", headers=_headers(), timeout=30, **kwargs)
    if resp.status_code == 401:
        return {"_error": "unauthorized", "_status": resp.status_code}
    return resp


def post(path: str, json=None, **kwargs):
    resp = session.post(f"{BASE_URL}{path}", headers=_headers(), json=json, timeout=60, **kwargs)
    if resp.status_code == 401:
        return {"_error": "unauthorized", "_status": resp.status_code}
    return resp


def delete(path: str, **kwargs):
    resp = session.delete(f"{BASE_URL}{path}", headers=_headers(), timeout=30, **kwargs)
    if resp.status_code == 401:
        return {"_error": "unauthorized", "_status": resp.status_code}
    return resp


def patch(path: str, json=None, **kwargs):
    resp = session.patch(f"{BASE_URL}{path}", headers=_headers(), json=json, timeout=30, **kwargs)
    if resp.status_code == 401:
        return {"_error": "unauthorized", "_status": resp.status_code}
    return resp


def health_ok() -> bool:
    try:
        r = get("/health")
        if isinstance(r, dict):
            return False
        return r.status_code < 500
    except Exception:
        return False
