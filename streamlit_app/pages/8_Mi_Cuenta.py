# 8_Mi_Cuenta.py – Página de cuenta de usuario

import os
import requests
import pandas as pd
import io
import streamlit as st
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.utils.auth_session import (
    is_authenticated,
    remember_current_page,
    get_auth_token,
)
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.ui.account_helpers import fetch_account_overview, get_plan_name

PRIMARY_METRICS_ORDER = [
    "leads_mes",
    "tareas",
    "notas",
    "exportaciones",
    "mensajes_ia",
]

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


def render_account_data(me: dict, plan_name: str):
    st.subheader("Datos de la cuenta")
    estado = "suspendido" if me.get("suspendido") else "activo"
    st.markdown(f"**Email:** {me.get('email','-')}")
    st.markdown(f"**Plan:** {plan_name.capitalize()}")
    st.markdown(f"**Estado:** {estado}")
    if me.get("fecha_creacion"):
        st.markdown(f"**Alta:** {me['fecha_creacion']}")


def render_subscription(subscription: dict):
    st.subheader("Suscripción")
    col1, col2 = st.columns([2, 1])
    with col1:
        next_renewal = subscription.get("next_renewal") or subscription.get("current_period_end") or "—"
        st.markdown(f"**Renovación:** {next_renewal}")
        st.markdown(f"**Estado pago:** {subscription.get('status','—')}")
    with col2:
        manage_url = subscription.get("manage_url")
        cancel_url = subscription.get("cancel_url")
        if manage_url:
            st.link_button("Gestionar plan", manage_url, use_container_width=True)
        if cancel_url:
            st.link_button("Cancelar", cancel_url, type="secondary", use_container_width=True)


def render_usage(usage: dict, quotas: dict):
    st.subheader("Uso del plan")

    extras = [k for k in (usage.keys() | quotas.keys()) if k not in PRIMARY_METRICS_ORDER]
    keys = PRIMARY_METRICS_ORDER + extras

    if not quotas:
        st.caption("Los cupos no han sido informados por el backend. Se muestran contadores a 0 / —.")

    for k in keys:
        usado = int(usage.get(k, 0) or 0)
        cupo = quotas.get(k, None)
        label = k.replace("_", " ").capitalize()

        col1, col2 = st.columns([3, 1])
        with col1:
            if isinstance(cupo, int) and cupo > 0:
                pct = min(usado / cupo, 1.0)
                st.progress(pct)
                st.markdown(f"**{label}:** {usado} / {cupo}")
            else:
                st.progress(0.0)
                st.markdown(f"**{label}:** {usado} / —")
        with col2:
            st.metric(label="Usado", value=usado)


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")
st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")

PAGE_NAME = "Cuenta"
remember_current_page(PAGE_NAME)
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

token = get_auth_token()
me, usage, quotas, subscription = fetch_account_overview(token)
user = me
st.session_state["user"] = user

if "auth_email" not in st.session_state and user:
    st.session_state["auth_email"] = user.get("email")

plan_name = get_plan_name(user)

with st.sidebar:
    logout_button()

headers = {"Authorization": f"Bearer {token}"}

st.title("Mi Cuenta")

render_account_data(user, plan_name)
render_subscription(subscription)

st.divider()
render_usage(usage, quotas)

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

