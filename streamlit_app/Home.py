import streamlit as st
from requests import ReadTimeout, ConnectTimeout
from requests.exceptions import ConnectionError

# --- Ensure project root is in sys.path
import sys
from pathlib import Path
import pathlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app.utils.auth_utils import ensure_session, logout_and_redirect
from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.cache_utils import cached_get
from streamlit_app.utils.cookies_utils import set_auth_token, init_cookie_manager_mount
from streamlit_app.utils import http_client
from streamlit_app.common_paths import APP_DIR, PAGES_DIR

init_cookie_manager_mount()

st.set_page_config(page_title="OpenSells", page_icon="🧩", layout="wide")


user, token = ensure_session(require_auth=False)

st.markdown("### ✨ Opensells")
st.markdown(
    '<div class="home-subtitle">IA de generación y gestión de leads para multiplicar x1000 tus ventas.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
<style>
.home-subtitle { font-size:1.05rem; opacity:.9; margin:-0.25rem 0 0.75rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

if not user:
    from json import JSONDecodeError

    def wait_for_backend(max_attempts: int = 5):
        with st.spinner("Conectando con el servidor..."):
            for i in range(1, max_attempts + 1):
                if http_client.health_ok():
                    return True
                st.info(f"Esperando al backend (intento {i}/{max_attempts})...")
                st.sleep(1.5 * i)
        return False

    def safe_json(resp):
        try:
            return resp.json()
        except JSONDecodeError:
            st.error(f"Respuesta no válida: {resp.text}")
            return {}

    st.subheader("Iniciar sesión")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar", use_container_width=True):
        if not wait_for_backend():
            st.error(
                "No puedo conectar con el backend ahora mismo. Por favor, vuelve a intentarlo en unos segundos.",
            )
            if st.button("Reintentar", type="secondary"):
                st.rerun()
            st.stop()

        try:
            r = http_client.post("/login", data={"username": email, "password": password})
        except (ReadTimeout, ConnectTimeout):
            st.error(
                "Tiempo de espera agotado al iniciar sesión. El servidor puede estar despertando. Pulsa 'Reintentar'.",
            )
            if st.button("Reintentar", type="secondary"):
                st.rerun()
            st.stop()
        except ConnectionError:
            st.error(
                "No hay conexión con el backend. Verifica BACKEND_URL o el estado del servidor.",
            )
            if st.button("Reintentar", type="secondary"):
                st.rerun()
            st.stop()

        if r.status_code == 200:
            data = safe_json(r)
            token = data.get("access_token")
            st.session_state["token"] = token
            st.session_state.email = email
            try:
                set_auth_token(token)
            except Exception:
                st.warning("No se pudieron guardar las cookies de sesión")
            ensure_session(require_auth=True)
            st.success("¡Sesión iniciada!")
            try:
                st.switch_page("streamlit/Home.py")
            except Exception:
                st.rerun()
        else:
            st.error("Credenciales inválidas o servicio no disponible. Intenta de nuevo.")

    if st.button("Registrarse", key="btn_register", use_container_width=True):
        try:
            r = http_client.post("/register", json={"email": email, "password": password})
            st.success(
                "Usuario registrado. Ahora inicia sesión." if r.status_code == 200 else "Error al registrar usuario.",
            )
        except Exception:
            st.error("Error al registrar usuario.")
    st.stop()

if st.sidebar.button("Cerrar sesión"):
    logout_and_redirect()


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
    "emails": "6_Emails.py",
    "suscripcion": "7_Suscripcion.py",
    "cuenta": "8_Mi_Cuenta.py",
}

plan = (user or {}).get("plan", "free")
suscripcion_activa = tiene_suscripcion_activa(plan)

nichos = cached_get("mis_nichos", st.session_state.token) or {}
num_nichos = len(nichos.get("nichos", []))

_tareas = cached_get("tareas_pendientes", st.session_state.token) or {}
num_tareas = len([t for t in _tareas.get("tareas", []) if not t.get("completado")])

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
            go(page_file)

with st.expander("Resumen de tu actividad"):
    st.write(f"**Número de nichos:** {num_nichos}")
    st.write(f"**Número de tareas pendientes:** {num_tareas}")
    if not suscripcion_activa:
        subscription_cta()
