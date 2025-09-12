import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

@st.cache_data(ttl=60)
def fetch_account_overview(auth_token: str):
    """Devuelve (me, usage, quotas) dicts. Nunca lanza; retorna {} en fallos."""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    me = {}
    usage = {}
    quotas = {}

    try:
        r = requests.get(f"{BACKEND_URL}/me", headers=headers, timeout=10)
        if r.ok:
            me = r.json() or {}
    except Exception:
        pass

    try:
        r = requests.get(f"{BACKEND_URL}/plan/usage", headers=headers, timeout=10)
        if r.ok:
            usage = r.json() or {}
    except Exception:
        pass

    try:
        r = requests.get(f"{BACKEND_URL}/plan/quotas", headers=headers, timeout=10)
        if r.ok:
            quotas = r.json() or {}
    except Exception:
        pass

    return me, usage, quotas

def get_plan_name(me: dict | None) -> str:
    """Devuelve el nombre del plan en minúsculas con fallback seguro."""
    if not isinstance(me, dict):
        return "free"
    plan = me.get("plan")
    if not plan:
        return "free"
    return str(plan).strip().lower()
