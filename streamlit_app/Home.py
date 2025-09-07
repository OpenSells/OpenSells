import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app.utils.constants import BRAND
from streamlit_app.utils.nav import go
from streamlit_app.utils.http_client import post, login as http_login
from streamlit_app.utils.auth_utils import (
    is_authenticated,
    save_session,
    restore_session_if_allowed,
)

st.set_page_config(page_title=f"{BRAND} — Accede a tu cuenta", layout="wide")

restore_session_if_allowed()

st.markdown(f"# {BRAND}")
st.subheader("Accede a tu cuenta")

if is_authenticated():
    st.info("Ya has iniciado sesión")
    st.button(
        "Ir a Búsqueda",
        use_container_width=True,
        on_click=lambda: go("pages/1_Busqueda.py"),
    )
else:
    tabs = st.tabs(["Entrar", "Crear cuenta"])

    with tabs[0]:
        with st.form("login_form"):
            username = st.text_input("Usuario o email")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
        if submitted:
            result = http_login(username, password)
            if isinstance(result, dict) and result.get("_error"):
                st.error("No autorizado. Revisa tus credenciales.")
            else:
                resp = result.get("response")
                token = result.get("token")
                if not token:
                    status = getattr(resp, "status_code", "unknown")
                    body = getattr(resp, "text", "")[:500]
                    st.error("No se recibió token de acceso.")
                    st.info(f"status: {status}\nbody: {body}")
                else:
                    save_session(token, username)
                    go("app.py")

    with tabs[1]:
        with st.form("register_form"):
            name = st.text_input("Nombre (opcional)")
            email = st.text_input("Email")
            password_reg = st.text_input("Contraseña", type="password")
            submitted_reg = st.form_submit_button("Crear cuenta", use_container_width=True)
        if submitted_reg:
            payload = {"email": email, "password": password_reg}
            if name:
                payload["name"] = name
            resp = post(
                "/register",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if isinstance(resp, dict) and resp.get("_error"):
                st.error("Error de autenticación.")
            elif getattr(resp, "status_code", 0) >= 400:
                if resp.status_code in (400, 409):
                    st.error("Ese email ya está registrado")
                else:
                    body = getattr(resp, "text", "")[:500]
                    st.error(f"Error al crear cuenta: {resp.status_code}. {body}")
            else:
                st.success("Cuenta creada. Iniciando sesión...")
                login_res = http_login(email, password_reg)
                if isinstance(login_res, dict) and login_res.get("_error"):
                    st.error("Error al iniciar sesión automáticamente.")
                else:
                    resp_login = login_res.get("response")
                    token = login_res.get("token")
                    if not token:
                        status = getattr(resp_login, "status_code", "unknown")
                        body = getattr(resp_login, "text", "")[:500]
                        st.error("No se recibió token de acceso.")
                        st.info(f"status: {status}\nbody: {body}")
                    else:
                        save_session(token, email)
                        go("app.py")

if __name__ == "__main__":
    pass
