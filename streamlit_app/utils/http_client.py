import os
import requests
from .auth_session import get_auth_token

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_session = requests.Session()

def _headers():
    h = {"Accept": "application/json"}
    tok = get_auth_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h

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
