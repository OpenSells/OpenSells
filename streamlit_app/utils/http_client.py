import os
import requests
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st
from streamlit_app.utils.auth_utils import clear_session

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEV = os.getenv("WRAPPER_DEV_MODE", "false").lower() == "true"

_session = requests.Session()
_retries = Retry(
    total=4,                # 1 intento + 4 reintentos = 5 en total
    backoff_factor=1.5,     # backoff exponencial: 1.5s, 3s, 4.5s, 6s...
    status_forcelist=(429, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]),
    raise_on_status=False,
)
_adapter = HTTPAdapter(max_retries=_retries, pool_connections=10, pool_maxsize=20)
_session.mount("http://", _adapter)
_session.mount("https://", _adapter)

_extra_headers: dict[str, str] = {}
_auth_token: str | None = None
_logged_backend_once = False

# timeouts: (connect_timeout, read_timeout)
DEFAULT_TIMEOUT = (5, 60)  # conectar rápido; dar margen al backend "cold start"
LONG_TIMEOUT = (5, 120)    # para /login si Render está frío


def _log_backend_once():
    """Muestra BACKEND_URL una sola vez en modo dev."""
    global _logged_backend_once
    if DEV and not _logged_backend_once:
        print(f"[DEV] BACKEND_URL: {BACKEND_URL}")
        _logged_backend_once = True


def _url(path: str) -> str:
    return urljoin(BACKEND_URL + "/", path.lstrip("/"))


def set_extra_headers(headers: dict[str, str] | None):
    """Define headers que se incluirán por defecto en todas las peticiones."""
    global _extra_headers
    _extra_headers = headers or {}


def set_auth_token(token: str | None):
    """Guarda el token a usar en futuras peticiones."""
    global _auth_token
    _auth_token = token


def _headers(path: str, headers: dict | None = None) -> dict:
    h = {"Accept": "application/json"}
    h.update(_extra_headers)
    if headers:
        h.update(headers)
    if _auth_token:
        h["Authorization"] = f"Bearer {_auth_token}"
    elif DEV and not path.endswith("/login"):
        print(f"[DEV][WARN] Request a {path} sin Authorization (token vacío).")
    return h


def _handle_401(resp):
    if resp is not None and getattr(resp, "status_code", None) == 401:
        if st.session_state.get("token"):
            st.warning("Token inválido o expirado. Inicia sesión nuevamente.")
        clear_session()
        try:
            st.switch_page("streamlit/Home.py")
        except Exception:
            st.rerun()
    return resp


def get(path: str, **kwargs):
    _log_backend_once()
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    headers = kwargs.pop("headers", None)
    resp = _session.get(_url(path), headers=_headers(path, headers), timeout=timeout, **kwargs)
    return _handle_401(resp)


def post(path: str, **kwargs):
    _log_backend_once()
    timeout = kwargs.pop("timeout", LONG_TIMEOUT)
    headers = kwargs.pop("headers", None)
    resp = _session.post(_url(path), headers=_headers(path, headers), timeout=timeout, **kwargs)
    return _handle_401(resp)


def delete(path: str, **kwargs):
    _log_backend_once()
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    headers = kwargs.pop("headers", None)
    resp = _session.delete(_url(path), headers=_headers(path, headers), timeout=timeout, **kwargs)
    return _handle_401(resp)


def health_ok() -> bool:
    try:
        # Intenta /health y, si no existe, cae a /
        r = get("/health", timeout=(3, 5))
        if r.status_code < 500:
            return True
    except Exception:
        pass
    try:
        r = get("/", timeout=(3, 5))
        return r.status_code < 500
    except Exception:
        return False
