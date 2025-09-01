import streamlit as st
from requests import ReadTimeout, ConnectTimeout
from requests.exceptions import ConnectionError

# Ensure project root in sys.path
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app.utils.auth_utils import save_session, restore_session_if_allowed
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client
from streamlit_app.utils.nav import go, HOME_PAGE

init_cookie_manager_mount()

st.set_page_config(page_title="Iniciar sesión", page_icon="🔐")

# Rehydrate session if possible and redirect if already logged in
restore_session_if_allowed()
if st.session_state.get("auth_token"):
    go(HOME_PAGE)
    st.stop()

st.subheader("Iniciar sesión")
email = st.text_input("Correo electrónico")
password = st.text_input("Contraseña", type="password")


def wait_for_backend(max_attempts: int = 5):
    with st.spinner("Conectando con el servidor..."):
        for i in range(1, max_attempts + 1):
            if http_client.health_ok():
                return True
            st.info(f"Esperando al backend (intento {i}/{max_attempts})...")
            st.sleep(1.5 * i)
    return False


def safe_json(resp):
    from json import JSONDecodeError

    try:
        return resp.json()
    except JSONDecodeError:
        st.error(f"Respuesta no válida: {resp.text}")
        return {}


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
        if token:
            save_session(token, email)
            resp_me = http_client.get("/me")
            if getattr(resp_me, "status_code", None) == 200:
                st.session_state["user"] = resp_me.json()
            st.success("¡Sesión iniciada!")
            go(HOME_PAGE)
        else:
            st.error("Credenciales inválidas o servicio no disponible. Intenta de nuevo.")
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

