# 4_Mi_Cuenta.py – Página de cuenta de usuario

import streamlit as st
import requests
from dotenv import load_dotenv
import os
import pandas as pd
import io

load_dotenv()
BACKEND_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Mi Cuenta", page_icon="⚙️")

# -------------------- Autenticación --------------------
if "token" not in st.session_state:
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# -------------------- Cargar email si falta --------------------
if "email" not in st.session_state:
    r = requests.get(f"{BACKEND_URL}/protegido", headers=headers)
    if r.status_code == 200:
        st.session_state.email = r.json()["mensaje"].split(",")[-1].strip()
    else:
        st.warning("No se pudo obtener tu email. Intenta volver a iniciar sesión.")
        st.stop()

# -------------------- Sección principal --------------------
st.title("⚙️ Mi Cuenta")

# -------------------- Plan actual --------------------
r = requests.get(f"{BACKEND_URL}/protegido", headers=headers)
if r.ok:
    plan_actual = r.json()["plan"] if "plan" in r.json() else "desconocido"
else:
    plan_actual = "desconocido"

st.subheader("📄 Plan actual")
st.markdown(f"Tu plan actual es: **{plan_actual}**")

if plan_actual == "free":
    st.warning("🚫 Algunas funciones están bloqueadas. Suscríbete para desbloquear la extracción y exportación de leads.")

# -------------------- Memoria del usuario --------------------
st.subheader("🧠 Memoria personalizada")
st.caption("Describe brevemente tu negocio, tus objetivos y el tipo de cliente que buscas.")

resp = requests.get(f"{BACKEND_URL}/mi_memoria", headers=headers)
memoria = resp.json().get("memoria", "") if resp.status_code == 200 else ""
nueva_memoria = st.text_area("Tu descripción de negocio", value=memoria, height=200)

if st.button("💾 Guardar memoria"):
    r = requests.post(f"{BACKEND_URL}/mi_memoria", headers=headers, json={"descripcion": nueva_memoria.strip()})
    st.success("Memoria guardada correctamente." if r.status_code == 200 else "Error al guardar la memoria.")

# -------------------- Estadísticas --------------------
st.subheader("📊 Estadísticas de uso")

nichos = requests.get(f"{BACKEND_URL}/mis_nichos", headers=headers).json().get("nichos", [])
leads_resp = requests.get(f"{BACKEND_URL}/exportar_todos_mis_leads", headers=headers)
total_leads = 0
if leads_resp.status_code == 200:
    df = pd.read_csv(io.BytesIO(leads_resp.content))
    total_leads = len(df)

tareas = requests.get(f"{BACKEND_URL}/tareas_pendientes", headers=headers).json().get("tareas", [])

st.markdown(f"""
- 🧠 **Nichos activos:** {len(nichos)}
- 🌐 **Leads extraídos:** {total_leads}
- 📋 **Tareas pendientes:** {len(tareas)}
""")

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
            r = requests.post(f"{BACKEND_URL}/cambiar_password", headers=headers, json=payload)
            if r.status_code == 200:
                st.success("Contraseña actualizada correctamente.")
            else:
                st.error(r.json().get("detail", "Error al cambiar contraseña."))

# -------------------- Suscripción --------------------
st.subheader("💳 Suscripción")

col1, col2 = st.columns(2)

url = None  # inicializamos la URL global para usar fuera del bloque

with col1:
    st.markdown("**Selecciona un plan:**")
    planes = {
        "Básico – 19,99/mes": "price_1RfOhcQYGhXE7WtIbH4hvWzp",
        "Pro – 49,99€/mes": "price_1RfOhRQYGhXE7WtIoSxrqsG5",
        "Ilimitado – 60€/mes": "price_1RfOhmQYGhXE7WtI49xFz469"
    }
    plan_elegido = st.selectbox("Planes disponibles", list(planes.keys()))
    if st.button("💳 Iniciar suscripción"):
        price_id = planes[plan_elegido]
        try:
            r = requests.post(f"{BACKEND_URL}/crear_checkout", headers=headers, params={"plan": price_id})
            if r.ok:
                url = r.json()["url"]
                st.success("Redirigiendo a Stripe...")
            else:
                st.error("No se pudo iniciar el pago.")
        except Exception as e:
            st.error(f"Error: {e}")

# Redirección fuera del bloque para evitar conflictos con scripts
if url:
    st.markdown(f"[👉 Pagar suscripción]({url})", unsafe_allow_html=True)
    st.markdown(f"""
<script>
window.open("{url}", "_self");
</script>
""", unsafe_allow_html=True)

with col2:
    if st.button("🧾 Gestionar suscripción"):
        try:
            r = requests.get(f"{BACKEND_URL}/portal_cliente", headers=headers)
            if r.ok:
                url_portal = r.json()["url"]
                st.success("Abriendo portal de cliente...")
                st.markdown(f"[👉 Abrir portal de Stripe]({url_portal})", unsafe_allow_html=True)
            else:
                st.error("No se pudo abrir el portal del cliente.")
        except Exception as e:
            st.error(f"Error: {e}")