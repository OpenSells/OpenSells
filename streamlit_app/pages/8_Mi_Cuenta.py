# 8_Mi_Cuenta.py – Página de cuenta de usuario

import os
import requests
import pandas as pd
import io
import streamlit as st
from dotenv import load_dotenv
from json import JSONDecodeError
from typing import Any

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.plan_utils import subscription_cta, force_redirect
from streamlit_app.utils.auth_session import (
    is_authenticated,
    remember_current_page,
    get_auth_token,
)
from streamlit_app.utils.logout_button import logout_button

# --- Helpers Uso del plan ---
PRIMARY_METRICS_ORDER = [
    "leads_mes",
    "tareas",
    "notas",
    "exportaciones",
    "mensajes_ia",
]

_NUM_CANDIDATES_USAGE = ["usado", "used", "count", "value", "current", "consumed"]
_NUM_CANDIDATES_QUOTA = ["limite", "limit", "max", "quota", "cap", "allowed", "total"]


def _to_number(x: Any, default: int = 0) -> int:
    """Convierte x a int de forma segura."""
    if x is None:
        return default
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, dict):
        for key in _NUM_CANDIDATES_USAGE + _NUM_CANDIDATES_QUOTA:
            if key in x and (
                isinstance(x[key], (int, float))
                or (
                    isinstance(x[key], str)
                    and x[key].strip().replace('.', '', 1).isdigit()
                )
            ):
                return _to_number(x[key], default)
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
        if for_quota:
            if isinstance(v, bool):
                out[k] = None if v else 0
                continue
            if isinstance(v, str) and v.lower() in ("ilimitado", "unlimited", "∞"):
                out[k] = None
                continue
        out[k] = _to_number(v, 0)
    return out

def _normalize_usage_and_quotas(mi_plan: dict) -> tuple[dict, dict]:
    """Acepta el JSON de /mi_plan y devuelve (usage, quotas) normalizados.
    Admite formatos:
      { plan, limites: {...}, uso: {...} }  ó  { plan, limits: {...}, usage: {...} }
    y mapea claves frecuentes.
    """
    limites = mi_plan.get("limites") or mi_plan.get("limits") or {}
    uso = mi_plan.get("uso") or mi_plan.get("usage") or {}

    def _norm(d: dict) -> dict:
        aliases = {
            "leads_mes":    ["leads_mes","leads_month","leads","searches","busquedas"],
            "tareas":       ["tareas","tasks"],
            "notas":        ["notas","notes"],
            "exportaciones":["exportaciones","exports"],
            "mensajes_ia":  ["mensajes_ia","ia_mensajes","ia_msgs","ai_messages"],
        }
        out = {}
        for std, ks in aliases.items():
            for k in ks:
                if k in d:
                    out[std] = d.get(k)
                    break
        for k, v in d.items():
            if k not in sum(aliases.values(), []):
                out[k] = v
        return out

    limites_alias = dict(limites)
    if "leads_mensuales" in limites_alias and "leads_mes" not in limites_alias:
        limites_alias["leads_mes"] = limites_alias.pop("leads_mensuales")
    if "ia_mensajes" in limites_alias and "mensajes_ia" not in limites_alias:
        limites_alias["mensajes_ia"] = limites_alias.pop("ia_mensajes")
    if "tareas_max" in limites_alias and "tareas" not in limites_alias:
        limites_alias["tareas"] = limites_alias.pop("tareas_max")
    if "csv_exportacion" in limites_alias and "exportaciones" not in limites_alias:
        val = limites_alias.pop("csv_exportacion")
        if isinstance(val, bool):
            limites_alias["exportaciones"] = None if val else 0
        else:
            limites_alias["exportaciones"] = val

    usage_raw = _norm(uso or {})
    quotas_raw = _norm(limites_alias or {})

    usage = _flatten_numbers(usage_raw, for_quota=False)
    quotas = _flatten_numbers(quotas_raw, for_quota=True)

    return usage, quotas

def _render_usage_section(usage: dict, quotas: dict):
    st.subheader("📊 Uso del plan")

    ordered = ["leads_mes", "tareas", "notas", "exportaciones", "mensajes_ia"]
    extras = [k for k in (usage.keys() | quotas.keys()) if k not in ordered]
    keys = ordered + extras

    if all(quotas.get(k) is None for k in keys):
        st.caption("Los cupos no han sido informados por el backend. Se muestran contadores a 0 / —.")

    for k in keys:
        usado = _to_number(usage.get(k), 0)
        cupo = quotas.get(k, None)
        label = k.replace("_", " ").capitalize()

        col1, col2 = st.columns([3, 1])
        with col1:
            if isinstance(cupo, int) and cupo > 0:
                pct = min(usado / cupo, 1.0)
                st.progress(pct)
                st.markdown(f"**{label}:** {usado} / {cupo}")
            elif cupo == 0:
                st.progress(1.0 if usado > 0 else 0.0)
                st.markdown(f"**{label}:** {usado} / 0")
            else:
                st.progress(0.0 if usado == 0 else 1.0)
                st.markdown(f"**{label}:** {usado} / —")
        with col2:
            st.metric("Usado", usado)

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
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

token = get_auth_token()
user = cached_get("/me", token) or {}
st.session_state["user"] = user
if "auth_email" not in st.session_state and user:
    st.session_state["auth_email"] = user.get("email")

# Recuperar plan y límites/uso
try:
    mi_plan = cached_get("/mi_plan", token) or {}
except Exception:
    mi_plan = {}
plan = mi_plan.get("plan", "free")

with st.sidebar:
    logout_button()

headers = {"Authorization": f"Bearer {token}"}

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
try:
    mi_plan = cached_get("/mi_plan", token) or {}
except Exception:
    mi_plan = {}
usage, quotas = _normalize_usage_and_quotas(mi_plan)
_render_usage_section(usage, quotas)
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
nichos = resp_nichos.get("nichos", []) if resp_nichos else []
leads_resp = requests.get(f"{BACKEND_URL}/exportar_todos_mis_leads", headers=headers)
if leads_resp.status_code == 200:
    df = pd.read_csv(io.BytesIO(leads_resp.content))
    total_leads = len(df)
else:
    total_leads = 0

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
