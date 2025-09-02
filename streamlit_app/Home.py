import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.cache_utils import cached_get
from streamlit_app.common_paths import PAGES_DIR
from streamlit_app.utils.nav import go
from streamlit_app.utils.auth_session import (
    is_authenticated,
    set_auth_token,
    remember_current_page,
    clear_auth_token,
    clear_page_remember,
    get_auth_token,
)
from streamlit_app.utils.http_client import post, get

st.set_page_config(page_title="OpenSells", page_icon="🧩", layout="wide")

PAGE_NAME = "Home"


def render_login():
    st.title("Wrapper Leads SaaS")
    st.subheader("Accede a tu cuenta")
    with st.form("login_form"):
        username = st.text_input("Usuario o email")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            resp = post("/login", json={"username": username, "password": password})
            if isinstance(resp, dict) and resp.get("_error"):
                st.error("No autorizado. Revisa tus credenciales.")
                return
            try:
                data = resp.json()
            except Exception:
                st.error("Respuesta inesperada del servidor.")
                return
            token = data.get("access_token") or data.get("token")
            if not token:
                st.error("No se recibió token de acceso.")
                return
            set_auth_token(token)
            st.success("Sesión iniciada.")
            st.rerun()


def render_logout_button():
    with st.sidebar:
        if st.button("Cerrar sesión", type="secondary"):
            clear_auth_token()
            clear_page_remember()
            st.rerun()


def render_home_private():
    token = get_auth_token()
    user = st.session_state.get("user")
    if token and not user:
        me = get("/me")
        if isinstance(me, dict) and me.get("_error") == "unauthorized":
            st.warning("Sesión expirada. Inicia sesión de nuevo.")
            clear_auth_token()
            st.rerun()
        if getattr(me, "status_code", None) == 200:
            user = me.json()
            st.session_state["user"] = user

    st.markdown(
        """
    <div style="text-align:center; margin-top: 1rem; margin-bottom: 1rem;">
        <h1 style="margin-bottom:0.25rem;">✨ Opensells</h1>
        <p style="font-size:1.1rem; margin-top:0;">IA de generación y gestión de leads para multiplicar x1000 tus ventas.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    def page_exists(name: str) -> bool:
        return (PAGES_DIR / name).exists()

    PAGES = {
        "assistant": "2_Asistente_Virtual.py",
        "busqueda": "1_Busqueda.py",
        "nichos": "3_Mis_Nichos.py",
        "tareas": "4_Tareas.py",
        "export": "5_Exportaciones.py",
        "emails": "6_Emails.py",
        "suscripcion": "7_Suscripcion.py",
        "cuenta": "8_Mi_Cuenta.py",
    }

    plan = (user or {}).get("plan", "free")
    suscripcion_activa = tiene_suscripcion_activa(plan)

    nichos = cached_get("mis_nichos", st.session_state.get("auth_token")) or {}
    num_nichos = len(nichos.get("nichos", []))

    _tareas = cached_get("tareas_pendientes", st.session_state.get("auth_token")) or []
    num_tareas = len([t for t in _tareas if not t.get("completado")])

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.subheader("🗨️ Modo Asistente Virtual (Beta)")
        st.markdown(
            "Interactúa por chat para pedir acciones y consejos. (La búsqueda de leads desde el asistente llegará más adelante)"
        )
        st.button(
            "🗨️ Asistente Virtual",
            use_container_width=True,
            disabled=not suscripcion_activa,
            on_click=lambda: go(f"pages/{PAGES['assistant']}")
        )
        if not suscripcion_activa:
            subscription_cta()

    with col2:
        st.subheader("📊 Modo Clásico")
        st.markdown("Genera leads únicos con cada búsqueda.")
        st.button(
            "🔎 Búsqueda de Leads",
            use_container_width=True,
            on_click=lambda: go(f"pages/{PAGES['busqueda']}")
        )

    st.divider()

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
                go(f"pages/{page_file}")

    with st.expander("Resumen de tu actividad"):
        st.write(f"**Número de nichos:** {num_nichos}")
        st.write(f"**Número de tareas pendientes:** {num_tareas}")
        if not suscripcion_activa:
            subscription_cta()


def main():
    if is_authenticated():
        remember_current_page(PAGE_NAME)
        render_logout_button()
        render_home_private()
    else:
        render_login()


if __name__ == "__main__":
    main()
