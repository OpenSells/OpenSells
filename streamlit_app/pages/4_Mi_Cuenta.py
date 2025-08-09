# 4_Mi_Cuenta.py – Página de cuenta de usuario

import os, streamlit as st
import requests
import pandas as pd
import io
from dotenv import load_dotenv
from json import JSONDecodeError
from cache_utils import cached_get, cached_post, limpiar_cache
from sidebar_utils import global_reset_button
from auth_utils import ensure_token_and_user, logout_button
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components


def _force_redirect(url: str):
    st.success("Redirigiendo a Stripe...")
    # Opción manual por si todo falla
    st.link_button(
        "👉 Abrir enlace si no se abre automáticamente", url, use_container_width=True
    )

    # Nonce para forzar ejecución en el cliente en el nuevo render
    nonce_key = "_redir_nonce"
    st.session_state[nonce_key] = st.session_state.get(nonce_key, 0) + 1

    # 1) Intento principal: JS Eval en la ventana superior
    try:
        streamlit_js_eval(
            js_expressions=f'window.top.location.href="{url}"',
            key=f"jsredir_{st.session_state[nonce_key]}"
        )
    except Exception:
        pass

    # 2) Fallback sólido con components.html y pequeño delay
    components.html(
        f'''
        <script>
        (function() {{
            // Un primer intento inmediato
            try {{ window.top.location.href = "{url}"; }} catch(e) {{}}
            // Un segundo intento tras un breve delay por si el primer render llega antes
            setTimeout(function() {{
                try {{ window.top.location.href = "{url}"; }} catch(e) {{}}
            }}, 50);
        }})();
        </script>
        ''',
        height=0,
    )

    st.stop()

load_dotenv()
BACKEND_URL = (
    st.secrets.get("BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or "https://opensells.onrender.com"
)
st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")
global_reset_button()
logout_button()
ensure_token_and_user()


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
elif plan == "basico":
    st.success("Tu plan actual es: basico")
elif plan == "premium":
    st.success("Tu plan actual es: premium")
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
                )
                if r.status_code == 200:
                    try:
                        data = r.json()
                    except JSONDecodeError:
                        st.error("Respuesta inválida del servidor.")
                    else:
                        url = data.get("url")
                        if url:
                            _force_redirect(url)
                        else:
                            st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error(
                        f"No se pudo iniciar el pago (status {r.status_code}): {r.text}"
                    )
            except Exception as e:
                st.error(f"Error: {e}")

with col2:
    if plan not in ["basico", "premium"]:
        st.button("🧾 Gestionar suscripción", disabled=True)
    else:
        if st.button("🧾 Gestionar suscripción"):
            try:
                r = requests.post(
                    f"{BACKEND_URL}/crear_portal_cliente",
                    headers=headers,
                )
                if r.status_code == 200:
                    data = r.json()
                    url_portal = data.get("url")
                    if url_portal:
                        _force_redirect(url_portal)
                    else:
                        st.error("La respuesta no contiene URL del portal.")
                else:
                    st.error(
                        f"No se pudo abrir el portal del cliente (status {r.status_code}): {r.text}"
                    )
            except Exception as e:
                st.error(f"Error: {e}")
