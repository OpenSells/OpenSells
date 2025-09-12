# 8_Mi_Cuenta.py – Página de cuenta de usuario

import os
import requests
import pandas as pd
import io
import streamlit as st
from dotenv import load_dotenv
from json import JSONDecodeError

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.plan_utils import force_redirect
from streamlit_app.utils.auth_session import (
    is_authenticated,
    remember_current_page,
    get_auth_token,
)
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.ui.account_helpers import fetch_account_overview, get_plan_name

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


def render_usage(usage: dict, quotas: dict):
    st.subheader("Uso del plan")
    keys = sorted(set(list(usage.keys()) + list(quotas.keys())))
    for k in keys:
        usado = usage.get(k, 0)
        cupo = quotas.get(k)
        label = k.replace("_", " ").capitalize()
        if isinstance(cupo, int) and cupo > 0:
            st.progress(min(usado / cupo, 1.0))
            st.markdown(f"- **{label}**: {usado} / {cupo}")
        else:
            st.markdown(f"- **{label}**: {usado} (sin límite declarado)")


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")
st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")

PAGE_NAME = "Cuenta"
remember_current_page(PAGE_NAME)
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

token = get_auth_token()
me, usage, quotas = fetch_account_overview(token)
user = me
st.session_state["user"] = user

if "auth_email" not in st.session_state and user:
    st.session_state["auth_email"] = user.get("email")

plan_name = get_plan_name(user)

with st.sidebar:
    logout_button()

headers = {"Authorization": f"Bearer {token}"}

# -------------------- Sección principal --------------------
st.title("⚙️ Mi Cuenta")

with st.container():
    st.subheader("Datos de la cuenta")
    st.markdown(f"**Email:** {user.get('email','-')}")
    st.markdown(f"**Plan:** {plan_name.capitalize()}")
    estado = "suspendido" if user.get("suspendido") else "activo"
    st.markdown(f"**Estado:** {estado}")
    if user.get("fecha_creacion"):
        st.markdown(f"**Alta:** {user['fecha_creacion']}")

st.divider()
render_usage(usage, quotas)
# if st.button("Ver planes / Actualizar"):
#     st.switch_page("pages/91_Planes.py")

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
total_leads = 0
if leads_resp.status_code == 200:
    df = pd.read_csv(io.BytesIO(leads_resp.content))
    total_leads = len(df)

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
    if plan_name not in ["basico", "premium"]:
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
