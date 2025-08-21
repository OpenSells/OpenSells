# 8_Mi_Cuenta.py – Página de cuenta de usuario

import os
import requests
import pandas as pd
import io
import streamlit as st
from dotenv import load_dotenv
from json import JSONDecodeError

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.utils.auth_utils import ensure_session, logout_and_redirect, get_backend_url
from streamlit_app.plan_utils import subscription_cta, force_redirect
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount

init_cookie_manager_mount()

load_dotenv()


st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")


user, token = ensure_session(require_auth=True)
plan = (user or {}).get("plan", "free")

if "email" not in st.session_state and user:
    st.session_state.email = user.get("email")

if st.sidebar.button("Cerrar sesión"):
    logout_and_redirect()

headers = {"Authorization": f"Bearer {st.session_state.token}"}


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

# -------------------- Memoria del usuario --------------------
st.subheader("🧠 Memoria personalizada")
st.caption(
    "Describe brevemente tu negocio, tus objetivos y el tipo de cliente que buscas."
)

resp = cached_get("mi_memoria", st.session_state.token)
memoria = resp.get("memoria", "") if resp else ""
nueva_memoria = st.text_area("Tu descripción de negocio", value=memoria, height=200)

if st.button("💾 Guardar memoria"):
    r = cached_post(
        "mi_memoria",
        st.session_state.token,
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

resp_nichos = cached_get("mis_nichos", st.session_state.token)
nichos = resp_nichos.get("nichos", []) if resp_nichos else []
leads_resp = requests.get(f"{get_backend_url()}/exportar_todos_mis_leads", headers=headers)
total_leads = 0
if leads_resp.status_code == 200:
    df = pd.read_csv(io.BytesIO(leads_resp.content))
    total_leads = len(df)

resp_tareas = cached_get("tareas_pendientes", st.session_state.token)
tareas = resp_tareas.get("tareas", []) if resp_tareas else []

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
            r = cached_post("cambiar_password", st.session_state.token, payload=payload)
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
                    f"{get_backend_url()}/crear_portal_pago",
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

with st.expander("Debug sesión/DB"):
    st.write("Token (prefijo):", (st.session_state.get("token") or "")[:12])
    st.write("Usuario:", st.session_state.get("user"))
    try:
        dbg_db = requests.get(f"{get_backend_url()}/debug-db").json()
    except Exception:
        dbg_db = {}
    try:
        dbg_snapshot = requests.get(
            f"{get_backend_url()}/debug-user-snapshot", headers=headers
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
                    f"{get_backend_url()}/crear_portal_cliente",
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
