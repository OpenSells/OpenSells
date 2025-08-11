import pathlib
import streamlit as st
from session_bootstrap import bootstrap

bootstrap()

from auth_utils import ensure_token_and_user, logout_button
from plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from cache_utils import cached_get

st.set_page_config(page_title="Wrapper Leads SaaS", page_icon="🧩", layout="wide")
logout_button()
ensure_token_and_user()

if "token" not in st.session_state:
    st.error("Debes iniciar sesión para ver esta página.")
    st.stop()

APP_DIR = pathlib.Path(__file__).parent
PAGES_DIR = APP_DIR / "pages"


def page_exists(name: str) -> bool:
    return (PAGES_DIR / name).exists()


def go(page_file: str):
    if not page_exists(page_file):
        st.warning("Esta página aún no está disponible.")
        return
    try:
        st.switch_page(f"pages/{page_file}")
    except Exception:
        st.page_link(f"pages/{page_file}", label="Abrir página", icon="➡️")


PAGES = {
    "assistant": "5_Asistente_Virtual.py",
    "busqueda": "1_Busqueda.py",
    "nichos": "2_Mis_Nichos.py",
    "tareas": "3_Tareas.py",
    "export": "4_Exportaciones.py",
    "cuenta": "6_Mi_Cuenta.py",
}

plan = obtener_plan(st.session_state.token)
suscripcion_activa = tiene_suscripcion_activa(plan)

nichos = cached_get("mis_nichos", st.session_state.token) or {}
num_nichos = len(nichos.get("nichos", []))

_tareas = cached_get("tareas_pendientes", st.session_state.token) or {}
num_tareas = len([t for t in _tareas.get("tareas", []) if not t.get("completado")])

st.title("Wrapper Leads SaaS")

col1, col2 = st.columns(2, gap="large")
with col1:
    st.subheader("🗨️ Modo Asistente Virtual")
    st.write("Chat interactivo que permite buscar leads, gestionar tareas, notas y estados.")
    abrir = st.button("Abrir Asistente", use_container_width=True, disabled=not suscripcion_activa)
    if abrir and suscripcion_activa:
        st.session_state["modo_seleccionado"] = "assistant"
        go(PAGES["assistant"])
    if not suscripcion_activa:
        subscription_cta()

with col2:
    st.subheader("📊 Modo Clásico")
    st.write("Navegación por las páginas actuales: búsqueda, nichos, tareas y exportaciones.")
    if st.button("Ir a Búsqueda de Leads", use_container_width=True):
        st.session_state["modo_seleccionado"] = "classic"
        go(PAGES["busqueda"])

st.markdown("---")

accesos = st.columns(4)
items = [
    ("📂 Mis Nichos", "nichos"),
    ("📋 Tareas", "tareas"),
    ("📤 Exportaciones", "export"),
    ("⚙️ Mi Cuenta", "cuenta"),
]
for col, (label, key) in zip(accesos, items):
    page_file = PAGES.get(key)
    if page_file and page_exists(page_file):
        if col.button(label, use_container_width=True):
            go(page_file)

with st.expander("Resumen de tu actividad"):
    st.write(f"**Plan actual:** {plan}")
    st.write(f"**Número de nichos:** {num_nichos}")
    st.write(f"**Número de tareas pendientes:** {num_tareas}")
    if not suscripcion_activa:
        subscription_cta()
