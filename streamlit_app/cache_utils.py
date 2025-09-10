import os
import streamlit as st
import requests
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlencode

load_dotenv()


def _safe_secret(name: str, default=None):
    """Safely retrieve configuration from env or Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")


def _build_url(endpoint: str) -> str:
    return f"{BACKEND_URL}{endpoint}" if endpoint.startswith("/") else f"{BACKEND_URL}/{endpoint}"

@st.cache_resource
def get_openai_client() -> OpenAI | None:
    """Return a cached OpenAI client or None if API key is missing."""
    key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=key) if key else None

@st.cache_data
def auth_headers(token: str) -> dict:
    """Authorization headers for a given token."""
    return {"Authorization": f"Bearer {token}"}

@st.cache_data
def cached_get(endpoint, token, query=None, nocache_key=None):
    """
    GET con caché de Streamlit. Si nocache_key cambia, se fuerza recarga.
    """
    url = _build_url(endpoint)
    headers = {"Authorization": f"Bearer {token}"}
    if query:
        url += "?" + urlencode(query)
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"[cached_get] Error: {e}")
    return {}


def cached_delete(endpoint, token, params=None):
    url = _build_url(endpoint)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.delete(url, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"[cached_delete] Error: {e}")
        return None


def cached_post(endpoint, token, payload=None, params=None):
    url = _build_url(endpoint)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, json=payload, params=params)
        if r.status_code == 200:
            # Limpiar cache relevante si es una acción conocida
            if endpoint in ["tarea_completada", "editar_tarea", "tarea_lead"]:
                if "_cache" in st.session_state:
                    for key in list(st.session_state._cache.keys()):
                        if "tareas_pendientes" in key or "tareas_lead" in key or "tareas_nicho" in key:
                            del st.session_state._cache[key]
            return r.json()
    except Exception as e:
        print(f"[cached_post] Error: {e}")
    return None


def limpiar_cache():
    """Clear all Streamlit caches."""
    if "_cache" in st.session_state:
        st.session_state._cache.clear()
    # Clear Streamlit's global caches as well
    st.cache_data.clear()
    st.cache_resource.clear()
