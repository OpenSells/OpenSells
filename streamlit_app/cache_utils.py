import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_app.utils import http_client

load_dotenv()


@st.cache_resource
def get_openai_client() -> OpenAI | None:
    """Return a cached OpenAI client or None if API key is missing."""
    key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=key) if key else None

@st.cache_data
def cached_get(endpoint, token, query=None, nocache_key=None):
    """GET con caché de Streamlit. Si nocache_key cambia, se fuerza recarga."""
    try:
        resp = http_client.get(f"/{endpoint}", params=query)
        if resp is not None and resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[cached_get] Error: {e}")
    return {}


def cached_delete(endpoint, token, params=None):
    try:
        r = http_client.delete(f"/{endpoint}", params=params)
        if r is not None and r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"[cached_delete] Error: {e}")
        return None


def cached_post(endpoint, token, payload=None, params=None):
    try:
        r = http_client.post(f"/{endpoint}", json=payload, params=params)
        if r is not None and r.status_code == 200:
            # Limpiar cache relevante si es una acción conocida
            if endpoint in ["tarea_completada", "editar_tarea", "tarea_lead"]:
                if "_cache" in st.session_state:
                    for key in list(st.session_state._cache.keys()):
                        if (
                            "tareas_pendientes" in key
                            or "tareas_lead" in key
                            or "tareas_nicho" in key
                        ):
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
