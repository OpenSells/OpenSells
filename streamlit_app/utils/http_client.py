import os
import requests
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st
from streamlit_app.utils.auth_utils import clear_session

BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com").rstrip("/")

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

# timeouts: (connect_timeout, read_timeout)
DEFAULT_TIMEOUT = (5, 60)  # conectar rápido; dar margen al backend "cold start"
LONG_TIMEOUT = (5, 120)    # para /login si Render está frío

def _url(path: str) -> str:
    return urljoin(BACKEND_URL + "/", path.lstrip("/"))

def _handle_401(resp):
    if resp is not None and getattr(resp, "status_code", None) == 401:
        clear_session()
        st.error("La sesión ha caducado. Por favor, inicia sesión de nuevo.")
        st.experimental_rerun()
    return resp


def get(path: str, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    resp = _session.get(_url(path), timeout=timeout, **kwargs)
    return _handle_401(resp)

def post(path: str, **kwargs):
    timeout = kwargs.pop("timeout", LONG_TIMEOUT)
    resp = _session.post(_url(path), timeout=timeout, **kwargs)
    return _handle_401(resp)


def delete(path: str, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    resp = _session.delete(_url(path), timeout=timeout, **kwargs)
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
