import os
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlencode

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com").rstrip("/")

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
    url = f"{BACKEND_URL}/{endpoint}"
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
    url = f"{BACKEND_URL}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.delete(url, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"[cached_delete] Error: {e}")
        return None

from streamlit import session_state

def cached_post(endpoint, token, payload=None, params=None):
    url = f"{BACKEND_URL}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, json=payload, params=params)
        if r.status_code == 200:
            # Limpiar cache relevante si es una acción conocida
            if endpoint in ["tarea_completada", "editar_tarea", "tarea_lead"]:
                if "_cache" in session_state:
                    for key in list(session_state._cache.keys()):
                        if "tareas_pendientes" in key or "tareas_lead" in key or "tareas_nicho" in key:
                            del session_state._cache[key]
            return r.json()
    except Exception as e:
        print(f"[cached_post] Error: {e}")
    return None
