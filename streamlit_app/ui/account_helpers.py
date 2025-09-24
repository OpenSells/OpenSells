import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEV_DEBUG = os.getenv("WRAPPER_DEBUG", "0") == "1"

CANDIDATE_PLAN = ["/plan/quotas", "/mi_plan"]
CANDIDATE_USAGE = ["/plan/usage", "/usage", "/stats/usage", "/me/usage"]
CANDIDATE_QUOTAS = ["/plan/quotas", "/quotas", "/plan/limits", "/limits"]
CANDIDATE_SUBSCR = [
    "/subscription/summary",
    "/billing/summary",
    "/plan/subscription",
    "/stripe/subscription",
]


@st.cache_data(ttl=60)
def fetch_account_overview(auth_token: str):
    """Devuelve (me, usage, quotas, subscription). Nunca lanza; retorna {} en fallos."""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    me, usage, quotas, subscription = {}, {}, {}, {}

    # Datos de cuenta
    try:
        r = requests.get(f"{BACKEND_URL}/me", headers=headers, timeout=10)
        if r.ok:
            me = r.json() or {}
    except Exception:
        pass

    # Plan (uso + cuotas combinados)
    for path in CANDIDATE_PLAN:
        try:
            r = requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=10)
            if r.ok and isinstance(r.json(), dict):
                data = r.json() or {}
                usage = data.get("usage") or {}
                quotas = data.get("limits") or {}
                if isinstance(usage, dict):
                    flat = {}
                    for k, v in usage.items():
                        if isinstance(v, dict):
                            if "used" in v:
                                flat[k] = v.get("used") or 0
                            elif "used_today" in v:
                                flat[k] = v.get("used_today") or 0
                            elif "current" in v:
                                flat[k] = v.get("current") or 0
                        else:
                            flat[k] = v
                    usage = flat
                break
        except Exception:
            continue

    # Uso
    if not usage:
        for path in CANDIDATE_USAGE:
            try:
                r = requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=10)
                if r.ok and isinstance(r.json(), dict):
                    usage = r.json() or {}
                    break
            except Exception:
                continue

    # Cuotas
    if not quotas:
        for path in CANDIDATE_QUOTAS:
            try:
                r = requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=10)
                if r.ok and isinstance(r.json(), dict):
                    quotas = r.json() or {}
                    break
            except Exception:
                continue

    # Suscripción
    for path in CANDIDATE_SUBSCR:
        try:
            r = requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=10)
            if r.ok and isinstance(r.json(), dict):
                subscription = r.json() or {}
                break
        except Exception:
            continue

    # Normalizar claves
    def norm(d: dict) -> dict:
        out: dict = dict(d or {})
        aliases = {
            "leads_mes": [
                "leads_mes",
                "leads_month",
                "leads",
                "searches",
                "busquedas",
                "lead_credits",
                "free_searches",
                "lead_credits_month",
                "searches_per_month",
            ],
            "tareas": ["tareas", "tasks", "tasks_active", "tasks_active_max"],
            "notas": ["notas", "notes"],
            "exportaciones": ["exportaciones", "exports", "csv_exports", "csv_exports_per_month"],
            "mensajes_ia": ["mensajes_ia", "ia_msgs", "ai_messages", "ai_daily_limit"],
        }
        for k_std, ks in aliases.items():
            for k in ks:
                if k in (d or {}):
                    out[k_std] = (d or {}).get(k)
                    break
        return out

    usage = norm(usage or {})
    quotas = norm(quotas or {})

    if DEV_DEBUG:
        st.caption("Debug Mi Cuenta")
        st.json({"me": me, "usage": usage, "quotas": quotas, "subscription": subscription})

    return me, usage, quotas, subscription


def get_plan_name(me: dict | None) -> str:
    """Devuelve el nombre del plan en minúsculas con fallback seguro."""
    if not isinstance(me, dict):
        return "free"
    plan = me.get("plan") or "free"
    return str(plan).strip().lower()
