import pathlib
import streamlit as st
from session_bootstrap import bootstrap

bootstrap()

from auth_utils import ensure_token_and_user, logout_button, save_token
from plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from cache_utils import cached_get
from cookies_utils import set_auth_cookies
from utils import full_width_button, http_client

st.set_page_config(page_title="OpenSells", page_icon="🧩", layout="wide")


def api_me(token: str):
    return http_client.get("/me", headers={"Authorization": f"Bearer {token}"})


user, token = ensure_token_and_user(api_me)

if not user:
    st.title("OpenSells")
    modo = st.radio("", ["Iniciar sesión", "Registrarse"], horizontal=True, key="auth_mode")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if modo == "Registrarse":
        password2 = st.text_input("Confirmar contraseña", type="password")

    if modo == "Iniciar sesión":
        if full_width_button("Iniciar sesión", key="btn_login"):
            try:
                r = http_client.post("/login", data={"username": email, "password": password})
            except Exception:
                st.error("No se pudo conectar con el servidor")
                st.stop()
            if r.status_code == 200:
                token = r.json().get("access_token")
                st.session_state.email = email
                try:
                    set_auth_cookies(token, email, days=7)
                except Exception:
                    pass
                save_token(token)
                st.rerun()
            else:
                detalle = (
                    r.json().get("detail")
                    if r.headers.get("content-type", "").startswith("application/json")
                    else r.text
                )
                st.error(detalle or "Credenciales inválidas")
    else:
        if full_width_button("Registrarse", key="btn_register"):
            if password != password2:
                st.error("Las contraseñas no coinciden")
            else:
                try:
                    r = http_client.post("/register", json={"email": email, "password": password})
                except Exception:
                    st.error("No se pudo conectar con el servidor")
                    st.stop()
                if r.status_code == 200:
                    login_resp = http_client.post(
                        "/login", data={"username": email, "password": password}
                    )
                    if login_resp.status_code == 200:
                        token = login_resp.json().get("access_token")
                        st.session_state.email = email
                        try:
                            set_auth_cookies(token, email, days=7)
                        except Exception:
                            pass
                        save_token(token)
                        st.rerun()
                    else:
                        st.info("Usuario registrado. Ahora puedes iniciar sesión.")
                else:
                    detalle = (
                        r.json().get("detail")
                        if r.headers.get("content-type", "").startswith("application/json")
                        else r.text
                    )
                    st.error(detalle or "Error al registrar usuario")
    st.stop()

logout_button()

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
    "assistant": "1_Asistente_Virtual.py",
    "busqueda": "2_Busqueda.py",
    "nichos": "3_Mis_Nichos.py",
    "tareas": "4_Tareas.py",
    "export": "5_Exportaciones.py",
    "suscripcion": "6_Suscripcion.py",
    "cuenta": "7_Mi_Cuenta.py",
}

plan = obtener_plan(st.session_state.token)
suscripcion_activa = tiene_suscripcion_activa(plan)

nichos = cached_get("mis_nichos", st.session_state.token) or {}
num_nichos = len(nichos.get("nichos", []))

_tareas = cached_get("tareas_pendientes", st.session_state.token) or {}
num_tareas = len([t for t in _tareas.get("tareas", []) if not t.get("completado")])

st.title("OpenSells")

col1, col2 = st.columns(2, gap="large")
with col1:
    st.subheader("🗨️ Modo Asistente Virtual")
    st.write("Chat interactivo que permite buscar leads, gestionar tareas, notas y estados.")
    st.button(
        "🗨️ Asistente Virtual",
        use_container_width=True,
        disabled=not suscripcion_activa,
        on_click=lambda: go(PAGES["assistant"]),
    )
    if not suscripcion_activa:
        subscription_cta()

with col2:
    st.subheader("📊 Modo Clásico")
    st.write("Navegación por las páginas actuales: búsqueda, nichos, tareas y exportaciones.")
    st.button(
        "🔎 Búsqueda de Leads",
        use_container_width=True,
        on_click=lambda: go(PAGES["busqueda"]),
    )

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
