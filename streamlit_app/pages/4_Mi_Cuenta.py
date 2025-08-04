# 4_Mi_Cuenta.py – Página de cuenta de usuario

import streamlit as st
import streamlit.components.v1 as components
import os
import requests
import pandas as pd
import io
from dotenv import load_dotenv
from json import JSONDecodeError
from cache_utils import cached_get, cached_post, limpiar_cache
from sidebar_utils import global_reset_button

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")
st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")
global_reset_button()


# -------------------- Autenticación --------------------
if "token" not in st.session_state:
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}


# -------------------- Cargar email si falta --------------------
if "email" not in st.session_state:
    r = cached_get("protegido", st.session_state.token)
    if r:
        st.session_state.email = r.get("mensaje", "").split(",")[-1].strip()
    else:
        st.warning("No se pudo obtener tu email. Intenta volver a iniciar sesión.")
        st.stop()

# -------------------- Sección principal --------------------
st.title("⚙️ Mi Cuenta")

# -------------------- Plan actual --------------------
# Validar token antes de hacer la petición
if "token" not in st.session_state:
    st.error("⚠️ Debes iniciar sesión para ver tu plan.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# Obtener plan del usuario
try:
    data_plan = cached_get("protegido", st.session_state.token)
    if data_plan:
        plan = data_plan.get("plan", "").strip().lower()
    else:
        st.warning("⚠️ No se pudo verificar tu suscripción. Vuelve a iniciar sesión.")
        plan = "desconocido"
except Exception as e:
    st.error(f"❌ Error de conexión al verificar el plan: {e}")
    plan = "desconocido"

st.text(f"Plan detectado: {plan}")

st.subheader("📄 Plan actual")
if plan == "free":
    st.success("Tu plan actual es: free")
    st.warning(
        "Algunas funciones están bloqueadas. Suscríbete para desbloquear la extracción y exportación de leads."
    )
elif plan == "pro":
    st.success("Tu plan actual es: pro")
elif plan == "ilimitado":
    st.success("Tu plan actual es: ilimitado")
else:
    st.warning("Tu plan actual es: desconocido")

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
leads_resp = requests.get(f"{BACKEND_URL}/exportar_todos_mis_leads", headers=headers)
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
        "Básico – 19,99/mes": os.getenv("STRIPE_PRICE_BASIC", ""),
        "Pro – 49,99€/mes": os.getenv("STRIPE_PRICE_PRO", ""),
        "Ilimitado – 60€/mes": os.getenv("STRIPE_PRICE_ILIMITADO", ""),
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
                )
                if r.status_code == 200:
                    try:
                        data = r.json()
                    except JSONDecodeError:
                        st.error("Respuesta inválida del servidor.")
                    else:
                        url = data.get("url")
                        if url:
                            st.success("Redirigiendo a Stripe...")
                            st.markdown(
                                f"[Haz clic aquí si no se abre automáticamente]({url})",
                                unsafe_allow_html=True,
                            )
                            components.html(
                                f"""
                                <script>
                                    window.location.href = '{url}';
                                </script>
                                """,
                                height=0,
                            )
                        else:
                            st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error("No se pudo iniciar el pago.")
            except Exception as e:
                st.error(f"Error: {e}")

with col2:
    if st.button("🧾 Gestionar suscripción"):
        try:
            r = cached_get("portal_cliente", st.session_state.token)
            if r and r.get("url"):
                url_portal = r.get("url", "")
                st.success("Abriendo portal de cliente...")
                st.markdown(
                    f"[👉 Abrir portal de Stripe]({url_portal})", unsafe_allow_html=True
                )
            else:
                st.error("No se pudo abrir el portal del cliente.")
        except Exception as e:
            st.error(f"Error: {e}")
