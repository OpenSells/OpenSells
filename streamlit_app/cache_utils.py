import os
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlencode

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")

@st.cache_resource
def get_openai_client() -> OpenAI | None:
    """Return a cached OpenAI client or None if API key is missing."""
    key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=key) if key else None

@st.cache_data
def auth_headers(token: str) -> dict:
    """Authorization headers for a given token."""
    return {"Authorization": f"Bearer {token}"}

@st.cache_data(ttl=300)
def cached_get(endpoint, token, query=None, nocache=False):
    url = f"{BACKEND_URL}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    if query:
        url += "?" + urlencode(query)
    try:
        if nocache:
            response = requests.get(url, headers=headers)
        else:
            if not hasattr(st.session_state, "_cache"):
                st.session_state._cache = {}
            if url not in st.session_state._cache:
                st.session_state._cache[url] = requests.get(url, headers=headers)
            response = st.session_state._cache[url]
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

def cached_post(endpoint, token, payload=None, params=None):
    url = f"{BACKEND_URL}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, json=payload, params=params)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"[cached_post] Error: {e}")
        return None
