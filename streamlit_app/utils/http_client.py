import os
import requests
from typing import Any, Dict, Optional
from .auth_session import get_auth_token

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_session = requests.Session()


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/json"}
    tok = get_auth_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


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
    resp = _session.post(url, data={"username": username, "password": password}, headers=_headers(), timeout=60)
    token = _extract_token(resp)
    if (not token or resp.status_code >= 400) and resp.status_code != 401:
        resp = _session.post(url, json={"username": username, "password": password}, headers=_headers(), timeout=60)
        token = _extract_token(resp)
    if resp.status_code == 401:
        return {"_error": "unauthorized"}
    return {"response": resp, "token": token}


def get(path: str, **kwargs):
    r = _session.get(f"{BASE_URL}{path}", headers=_headers(), timeout=30, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r


def post(path: str, json=None, **kwargs):
    r = _session.post(f"{BASE_URL}{path}", headers=_headers(), json=json, timeout=60, **kwargs)
    if r.status_code == 401:
        return {"_error": "unauthorized", "_status": 401}
    return r
