import time
import streamlit as st
from session_bootstrap import bootstrap

bootstrap()

from auth_utils import ensure_token_and_user, logout_button
from plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from cache_utils import cached_get

st.set_page_config(page_title="OpenSells", page_icon="🧩")
logout_button()
ensure_token_and_user()

if "token" not in st.session_state:
    st.error("Debes iniciar sesión para ver esta página.")
    st.stop()

plan = obtener_plan(st.session_state.token)
suscripcion_activa = tiene_suscripcion_activa(plan)

nichos_resp = cached_get("mis_nichos", st.session_state.token, nocache_key=time.time())
num_nichos = len(nichos_resp.get("nichos", [])) if nichos_resp else 0

tareas_resp = cached_get("tareas_pendientes", st.session_state.token, nocache_key=time.time())
num_tareas = (
    len([t for t in tareas_resp.get("tareas", []) if not t.get("completado")])
    if tareas_resp
    else 0
)

st.title("OpenSells")

col1, col2 = st.columns(2, gap="large")
with col1:
    st.subheader("🧠 Modo Asistente Virtual")
    st.write(
        "Chat interactivo que permite buscar leads, gestionar tareas, notas y estados."
    )
    abrir = st.button(
        "Abrir Asistente", use_container_width=True, disabled=not suscripcion_activa
    )
    if abrir and suscripcion_activa:
        try:
            st.switch_page("pages/5_Asistente_Virtual.py")
        except Exception:
            st.session_state._nextpage = "pages/5_Asistente_Virtual.py"
            st.experimental_rerun()
    if not suscripcion_activa:
        st.warning("Tu plan actual no incluye el asistente virtual.")
        subscription_cta()

with col2:
    st.subheader("🗂️ Modo Clásico")
    st.write(
        "Navegación por las páginas actuales: búsqueda, nichos, tareas y exportaciones."
    )
    if st.button("Ir a Búsqueda de Leads", use_container_width=True):
        try:
            st.switch_page("pages/1_Busqueda.py")
        except Exception:
            st.session_state._nextpage = "pages/1_Busqueda.py"
            st.experimental_rerun()

st.markdown("---")

accesos = st.columns(4)
links = [
    ("📂 Mis Nichos", "pages/2_Mis_Nichos.py"),
    ("📋 Tareas", "pages/3_Tareas.py"),
    ("📤 Exportaciones", "pages/4_Exportaciones.py"),
    ("⚙️ Mi Cuenta", "pages/6_Mi_Cuenta.py"),
]
for col, (label, page) in zip(accesos, links):
    if col.button(label, use_container_width=True):
        try:
            st.switch_page(page)
        except Exception:
            st.session_state._nextpage = page
            st.experimental_rerun()

with st.expander("Resumen de tu actividad"):
    st.write(f"**Plan actual:** {plan}")
    st.write(f"**Número de nichos:** {num_nichos}")
    st.write(f"**Número de tareas pendientes:** {num_tareas}")
    if not suscripcion_activa:
        subscription_cta()
