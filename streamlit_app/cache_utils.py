import os
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

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
def cached_get(endpoint: str, token: str, **params):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{BACKEND_URL}/{endpoint}", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

@st.cache_data(ttl=300)
def cached_post(endpoint: str, token: str, payload: dict | None = None, **params):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(
            f"{BACKEND_URL}/{endpoint}",
            headers=headers,
            json=payload,
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}
