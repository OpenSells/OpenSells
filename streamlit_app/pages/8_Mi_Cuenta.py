# --- Path bootstrap (asegura que la raíz del repo esté en sys.path) ---
import os, sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
STREAMLIT_DIR = THIS_DIR
if os.path.basename(STREAMLIT_DIR) != "streamlit_app":
    STREAMLIT_DIR = os.path.dirname(STREAMLIT_DIR)
ROOT_DIR = os.path.dirname(STREAMLIT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# ----------------------------------------------------------------------

# 8_Mi_Cuenta.py – Página de cuenta de usuario

import requests
import streamlit as st
from dotenv import load_dotenv
from json import JSONDecodeError
from typing import Any

from streamlit_app.auth_client import (
    ensure_authenticated,
    current_token,
    auth_headers as auth_client_headers,
)
from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.plan_utils import subscription_cta, force_redirect
from streamlit_app.utils.auth_session import remember_current_page
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.components.ui import render_whatsapp_fab

# --- KPIs visibles y etiquetas ES ---
PRIMARY_KEYS = [
    "searches_per_month",
    "mensajes_ia",
    "leads_mes",
]

LABELS_ES = {
    "searches_per_month": "Búsquedas/mes",
    "mensajes_ia": "Mensajes IA",
    "leads_mes": "Leads extraídos (mes)",
}

# Aliases canónicos -> lista de alias aceptados (uso y cuotas)
ALIASES_MAP = {
    "searches_per_month": [
        "searches_per_month",
        "searches",
        "busquedas_mes",
        "leads_month",
        "free_searches",
    ],
    "mensajes_ia": [
        "mensajes_ia",
        "ia_mensajes",
        "ia_msgs",
        "ai_messages",
        "ai daily limit",
        "ai_daily_limit",
    ],
    "leads_mes": [
        "leads_mes",
        "leads",
        "leads_month",
        "lead_credits",
        "lead_credits_month",
        "lead_usage",
        "leads_used",
    ],
}

PLAN_ENDPOINTS = ("/mi_plan", "/plan/quotas")


def _fmt_limit(value) -> str:
    if value is None:
        return "Sin límite"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return f"{int(value)}"
    return str(value)


def _period_humano(period_yyyymm: str | None) -> str | None:
    if not period_yyyymm:
        return None
    period = str(period_yyyymm).strip()
    if len(period) != 6 or not period.isdigit():
        return None
    year = int(period[:4])
    month = int(period[4:])
    meses = [
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    if 1 <= month <= 12:
        nombre_mes = meses[month]
    else:
        nombre_mes = f"{month:02d}"
    return f"{nombre_mes} {year}"


def _to_number(x: Any, default: int = 0) -> int:
    if x is None:
        return default
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, dict):
        for k in (
            "usado",
            "used",
            "count",
            "value",
            "current",
            "consumed",
            "limit",
            "max",
            "quota",
            "total",
            "cap",
            "allowed",
        ):
            if k in x:
                return _to_number(x[k], default)
        return default
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        try:
            return int(float(s))
        except Exception:
            return default
    return default


def _flatten_numbers(d: dict, for_quota: bool = False) -> dict:
    """Devuelve un dict con mismos keys pero valores enteros (o None si no aplica)."""
    out: dict[str, int | None] = {}
    for k, v in (d or {}).items():
        if v is None:
            out[k] = None if for_quota else 0
            continue
        if for_quota:
            if isinstance(v, bool):
                out[k] = None if v else 0
                continue
            if isinstance(v, str) and v.lower() in (
                "ilimitado",
                "unlimited",
                "∞",
                "sin limite",
                "sin límite",
            ):
                out[k] = None
                continue
        out[k] = _to_number(v, 0)
    return out


def _coalesce_aliases(raw: dict, is_quota: bool = False) -> dict:
    """
    Toma un dict (usage o quotas) y devuelve SOLO las claves canónicas de PRIMARY_KEYS,
    resolviendo alias y evitando duplicados. Si hay varios alias presentes,
    usa el valor NUMÉRICO MAYOR (más conservador para 'usado') y para cuota el MAYOR límite.
    """
    out = {}
    for std, aliases in ALIASES_MAP.items():
        values = []
        for a in aliases:
            if a in raw:
                values.append(raw[a])
        if not values:
            continue
        nums = []
        saw_none = False
        for v in values:
            if is_quota and v is None:
                saw_none = True
                continue
            if is_quota and isinstance(v, bool) and v is True:
                saw_none = True
            elif is_quota and isinstance(v, str) and v.lower() in (
                "ilimitado",
                "unlimited",
                "∞",
            ):
                saw_none = True
            else:
                nums.append(_to_number(v, 0))
        if is_quota:
            out[std] = None if saw_none else (max(nums) if nums else 0)
        else:
            out[std] = max(nums) if nums else 0
    return out

def _normalize_usage_and_quotas(mi_plan: dict) -> tuple[dict, dict]:
    """Acepta el JSON de /plan/quotas y devuelve (usage, quotas) normalizados.
    Admite formatos:
      { plan, limites: {...}, uso: {...} }  ó  { plan, limits: {...}, usage: {...} }
    y mapea claves frecuentes.
    """
    limites = mi_plan.get("limites") or mi_plan.get("limits") or {}
    uso = mi_plan.get("uso") or mi_plan.get("usage") or {}

    usage_norm = _flatten_numbers(uso or {}, for_quota=False)
    quotas_norm = _flatten_numbers(limites or {}, for_quota=True)

    # Derivar métricas específicas del endpoint /mi_plan
    if "leads_mes" not in usage_norm and "leads" in usage_norm:
        usage_norm["leads_mes"] = usage_norm.get("leads", 0)

    lead_limit = quotas_norm.get("lead_credits_month")
    if lead_limit is None:
        searches_limit = quotas_norm.get("searches_per_month")
        cap_limit = quotas_norm.get("leads_cap_per_search")
        if searches_limit is None or cap_limit is None:
            lead_limit = None
        else:
            lead_limit = searches_limit * cap_limit
    quotas_norm["leads_mes"] = lead_limit

    usage_final = _coalesce_aliases(usage_norm, is_quota=False)
    quotas_final = _coalesce_aliases(quotas_norm, is_quota=True)

    for key in PRIMARY_KEYS:
        usage_final.setdefault(key, 0)
        quotas_final.setdefault(key, None)

    return usage_final, quotas_final


def _render_row(label: str, usado: int, cupo):
    col1, col2 = st.columns([3,1])
    cupo_display = _fmt_limit(cupo)
    with col1:
        limit_is_number = isinstance(cupo, (int, float)) and not isinstance(cupo, bool)
        if limit_is_number and cupo > 0:
            pct = min(usado / cupo, 1.0)
            st.progress(pct)
            st.markdown(f"**{label}:** {usado} / {cupo_display}")
        elif limit_is_number and cupo == 0:
            st.progress(1.0 if usado > 0 else 0.0)
            st.markdown(f"**{label}:** {usado} / {cupo_display}")
        else:
            st.progress(0.0 if usado == 0 else 1.0)
            st.markdown(f"**{label}:** {usado} / {cupo_display}")
    with col2:
        st.metric("Usado", usado)


def _pretty_label(key: str) -> str:
    return LABELS_ES.get(key, key.replace("_"," ").capitalize())


def _render_usage_section(usage: dict, quotas: dict, raw_plan: dict):
    st.subheader("📊 Uso del plan")
    raw_usage = raw_plan.get("uso") or raw_plan.get("usage") or {}
    raw_limits = raw_plan.get("limites") or raw_plan.get("limits") or {}
    period = None
    if isinstance(raw_usage.get("leads"), dict):
        lead_usage = raw_usage.get("leads", {})
        period = lead_usage.get("period") or lead_usage.get("periodo")
    if not period:
        for value in raw_usage.values():
            if isinstance(value, dict):
                candidate = value.get("period") or value.get("periodo")
                if candidate:
                    period = candidate
                    break
    tasks_active_data = raw_usage.get("tasks_active") or {}
    tasks_active_current = _to_number(tasks_active_data.get("current"), 0)
    tasks_active_limit_raw = raw_limits.get("tasks_active_max")
    if isinstance(tasks_active_limit_raw, bool):
        if tasks_active_limit_raw:
            tasks_active_limit = None
        else:
            tasks_active_limit = 0
    elif tasks_active_limit_raw is None:
        tasks_active_limit = None
    else:
        tasks_active_limit = _to_number(tasks_active_limit_raw, 0)
    for key in PRIMARY_KEYS:
        usado = _to_number(usage.get(key), 0)
        cupo  = quotas.get(key, None)  # None => sin límite declarado
        _render_row(_pretty_label(key), usado, cupo)
    _render_row("Tareas activas", tasks_active_current, tasks_active_limit)
    period_humano = _period_humano(period)
    if period_humano:
        st.caption(f"Periodo: {period_humano}")


def _fetch_plan_payload(token: str) -> dict:
    for endpoint in PLAN_ENDPOINTS:
        try:
            data = cached_get(endpoint, token)
        except Exception:
            data = {}
        if data:
            return data
    return {}

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

def is_debug_ui_enabled():
    env_ok = os.getenv("DEBUG_UI", "").strip().lower() == "true"
    secrets_ok = False
    try:
        secrets_ok = bool(st.secrets.get("DEBUG_UI", False))
    except Exception:
        secrets_ok = False
    return env_ok or secrets_ok

BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")
st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")

PAGE_NAME = "Cuenta"
remember_current_page(PAGE_NAME)
if not ensure_authenticated():
    st.title(PAGE_NAME)
    st.warning("Sesión expirada. Vuelve a iniciar sesión.")
    st.stop()

token = current_token()
user = cached_get("/me", token) if token else {}
if user:
    st.session_state["user"] = user
    if "auth_email" not in st.session_state:
        st.session_state["auth_email"] = user.get("email")

# Recuperar plan y límites/uso
mi_plan = _fetch_plan_payload(token) or {}
plan = str(mi_plan.get("plan", "free")).strip().lower()

with st.sidebar:
    logout_button()

headers = auth_client_headers()

# -------------------- Sección principal --------------------
st.title("⚙️ Mi Cuenta")

# -------------------- Plan actual --------------------
st.subheader("📄 Plan actual")
if plan == "free":
    st.success("Tu plan actual es: free")
    st.warning(
        "Algunas funciones están bloqueadas. Suscríbete para desbloquear la extracción y exportación de leads."
    )
    subscription_cta()
elif plan == "basico":
    st.success("Tu plan actual es: basico")
elif plan == "premium":
    st.success("Tu plan actual es: premium")
else:
    st.success(f"Tu plan actual es: {plan}")

# --- NUEVO: Uso del plan (debajo de "📄 Plan actual") ---
usage, quotas = _normalize_usage_and_quotas(mi_plan)
_render_usage_section(usage, quotas, mi_plan)
st.divider()

# -------------------- Memoria del usuario --------------------
st.subheader("🧠 Memoria personalizada")
st.caption(
    "Describe brevemente tu negocio, tus objetivos y el tipo de cliente que buscas."
)

resp = cached_get("/mi_memoria", token)
memoria = resp.get("memoria", "") if resp else ""
nueva_memoria = st.text_area("Tu descripción de negocio", value=memoria, height=200)

if st.button("💾 Guardar memoria"):
    r = cached_post(
        "mi_memoria",
        token,
        payload={"descripcion": nueva_memoria.strip()},
    )
    if r:
        limpiar_cache()
        st.success("Memoria guardada correctamente.")
        st.rerun()
    else:
        st.error("Error al guardar la memoria.")

# -------------------- Estadísticas --------------------
st.subheader("📊 Estadísticas de uso")

resp_nichos = cached_get("/mis_nichos", token)
if isinstance(resp_nichos, list):
    nichos = resp_nichos
elif isinstance(resp_nichos, dict):
    nichos = resp_nichos.get("nichos", [])
else:
    nichos = []
lead_usage_value = usage.get("leads_mes") if usage else 0
if lead_usage_value in (None, ""):
    lead_usage_value = usage.get("leads") if usage else 0
total_leads = _to_number(lead_usage_value, 0)

resp_tareas = cached_get("tareas_pendientes", token)
tareas = resp_tareas or []

st.markdown(
    f"""
- 🧠 **Nichos activos:** {len(nichos)}
- 🌐 **Leads extraídos:** {total_leads}
- 📋 **Tareas pendientes:** {len(tareas)}
"""
)

# -------------------- Cambio de contraseña --------------------
st.subheader("🔐 Cambiar contraseña")
with st.form("form_pass"):
    actual = st.text_input("Contraseña actual", type="password")
    nueva = st.text_input("Nueva contraseña", type="password")
    confirmar = st.text_input("Confirmar nueva contraseña", type="password")
    enviar = st.form_submit_button("Actualizar contraseña")

    if enviar:
        if not all([actual, nueva, confirmar]):
            st.warning("Completa todos los campos.")
        elif nueva != confirmar:
            st.warning("Las contraseñas no coinciden.")
        else:
            payload = {"actual": actual, "nueva": nueva}
            r = cached_post("cambiar_password", token, payload=payload)
            if r:
                st.success("Contraseña actualizada correctamente.")
            else:
                st.error(
                    r.get("detail", "Error al cambiar contraseña.")
                    if isinstance(r, dict)
                    else "Error al cambiar contraseña."
                )

# -------------------- Suscripción --------------------
st.subheader("💳 Suscripción")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Selecciona un plan:**")
    planes = {
        "Básico – 14,99€/mes": os.getenv("STRIPE_PRICE_BASICO", ""),
        "Premium – 49,99€/mes": os.getenv("STRIPE_PRICE_PREMIUM", ""),
    }
    if not all(planes.values()):
        st.error("Faltan configuraciones de precios de Stripe.")
    else:
        plan_elegido = st.selectbox("Planes disponibles", list(planes.keys()))
        if st.button("💳 Iniciar suscripción"):
            price_id = planes[plan_elegido]
            try:
                r = requests.post(
                    f"{BACKEND_URL}/crear_portal_pago",
                    headers=headers,
                    params={"plan": price_id},
                    timeout=30,
                )
                if r.status_code == 200:
                    try:
                        data = r.json()
                    except JSONDecodeError:
                        st.error("Respuesta inválida del servidor.")
                    else:
                        url = data.get("url")
                        if url:
                            force_redirect(url)
                        else:
                            st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error("No se pudo iniciar el pago.")
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")
if is_debug_ui_enabled():
    with st.expander("Debug sesión"):
        st.write("Token (prefijo):", (st.session_state.get("token") or "")[:12])
        st.write("Usuario:", st.session_state.get("user"))
        try:
            dbg_db = requests.get(f"{BACKEND_URL}/debug-db").json()
        except Exception:
            dbg_db = {}
        try:
            dbg_snapshot = requests.get(
                f"{BACKEND_URL}/debug-user-snapshot", headers=headers
            ).json()
        except Exception:
            dbg_snapshot = {}
        st.write("Email /me:", dbg_snapshot.get("email_me"))
        st.write("Email /me lower:", dbg_snapshot.get("email_me_lower"))
        st.write("DB URL prefix:", (dbg_db.get("database_url") or "")[:16])
        st.write("# Nichos:", dbg_snapshot.get("nichos_count"))
        st.write("# Leads:", dbg_snapshot.get("leads_total_count"))

with col2:
    if plan not in ["basico", "premium"]:
        st.button("🧾 Gestionar suscripción", disabled=True)
    else:
        if st.button("🧾 Gestionar suscripción"):
            try:
                r = requests.post(
                    f"{BACKEND_URL}/crear_portal_cliente",
                    headers=headers,
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    url_portal = data.get("url")
                    if url_portal:
                        force_redirect(url_portal)
                    else:
                        st.error("La respuesta no contiene URL del portal.")
                else:
                    st.error("No se pudo abrir el portal del cliente.")
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")
