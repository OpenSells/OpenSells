# 8_Mi_Cuenta.py – Página de cuenta de usuario

import os
import requests
import pandas as pd
import io
import streamlit as st
from dotenv import load_dotenv
from json import JSONDecodeError

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
import streamlit_app.utils.http_client as http_client
from streamlit_app.plan_utils import (
    subscription_cta,
    force_redirect,
    resolve_user_plan,
    render_plan_panel,
    PLAN_ALIASES,
)
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button

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
user = st.session_state.get("user")
if token and not user:
    resp_user = http_client.get("/me")
    if isinstance(resp_user, dict) and resp_user.get("_error") == "unauthorized":
        st.warning("Sesión expirada. Vuelve a iniciar sesión.")
        st.stop()
    if getattr(resp_user, "status_code", None) == 200:
        user = resp_user.json()
        st.session_state["user"] = user
plan_info = resolve_user_plan(token)
plan = plan_info.get("plan", "free")

if "auth_email" not in st.session_state and user:
    st.session_state["auth_email"] = user.get("email")

with st.sidebar:
    logout_button()
    render_plan_panel(plan_info)

headers = {"Authorization": f"Bearer {token}"}


# -------------------- Sección principal --------------------
st.title("⚙️ Mi Cuenta")
render_plan_panel(plan_info)

# -------------------- Plan actual --------------------
st.subheader("📄 Plan actual")
alias = PLAN_ALIASES.get(plan, plan)
st.success(f"Tu plan actual es: {alias}")
if plan == "free":
    st.warning(
        "Algunas funciones están bloqueadas. Suscríbete para desbloquear la extracción y exportación de leads."
    )
    subscription_cta()

# -------------------- Memoria del usuario --------------------
st.subheader("🧠 Memoria personalizada")
st.caption(
    "Describe brevemente tu negocio, tus objetivos y el tipo de cliente que buscas."
)

resp = cached_get("mi_memoria", token)
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

resp_nichos = cached_get("mis_nichos", token)
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
