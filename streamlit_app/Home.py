import re
import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app.utils.constants import (
    BRAND,
    LEADS_PAGE_PATH,
    ASSISTANT_PAGE_PATH,
)
from streamlit_app.utils.nav import go  # <- nav se importa del submódulo, no del paquete raíz
from streamlit_app.utils.http_client import post, login as http_login
from streamlit_app.utils.auth_utils import (
    is_authenticated,
    save_session,
    restore_session_if_allowed,
)
from streamlit_app.utils.logout_button import logout_button


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _card(title: str, desc: str, on_click):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.button(f"{title}\n{desc}", use_container_width=True, on_click=on_click)
    st.markdown("</div>", unsafe_allow_html=True)


restore_session_if_allowed()

auth = is_authenticated()
if auth:
    st.set_page_config(page_title=f"{BRAND} — Inicio", layout="wide")
else:
    st.set_page_config(page_title=f"{BRAND} — Accede a tu cuenta", layout="wide")

st.markdown(
    """
    <style>
    .block-container{max-width:1100px;padding-top:2rem;}
    .hero{display:flex;justify-content:space-between;align-items:center;margin-bottom:3rem;}
    .session-badge{font-size:0.875rem;background:#eef2ff;padding:0.25rem 0.75rem;border-radius:9999px;}
    .card{margin-bottom:1rem;}
    .card .stButton>button{background:#f8fafc;border:1px solid #e6e8eb;border-radius:16px;padding:20px 24px;box-shadow:0 1px 2px rgba(0,0,0,.04);transition:transform .08s ease,box-shadow .2s ease;width:100%;text-align:left;font-size:19px;white-space:normal;}
    .card .stButton>button:hover{transform:translateY(-2px);box-shadow:0 4px 6px rgba(0,0,0,.07);background:#f1f5f9;border-color:#d5d8dc;}
    </style>
    """,
    unsafe_allow_html=True,
)

session_text = "Sesión activa" if auth else "Sesión no iniciada"
st.markdown(
    f"""
    <div class="hero">
      <div>
        <h1>{BRAND}</h1>
        <p>Genera y gestiona leads de forma simple.</p>
      </div>
      <span class="session-badge">{session_text}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if auth:
    st.markdown("### ¿Qué quieres hacer hoy?")
    cols = st.columns(2)
    with cols[0]:
        _card(
            "🔎 Búsqueda de leads",
            "Encuentra y guarda leads por nicho desde Google/Maps",
            lambda: st.switch_page(LEADS_PAGE_PATH),
        )
    with cols[1]:
        _card(
            "🤖 Asistente virtual (beta)",
            "Haz preguntas y lanza búsquedas guiadas con IA",
            lambda: st.switch_page(ASSISTANT_PAGE_PATH),
        )

    st.markdown("### Más herramientas")
    logout_button()
    if Path("streamlit_app/pages/8_Mi_Cuenta.py").exists():
        st.page_link("pages/8_Mi_Cuenta.py", label="Mi cuenta")
else:
    tabs = st.tabs(["Entrar", "Crear cuenta"])

    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="tucorreo@ejemplo.com")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Iniciar sesión", use_container_width=True)
        if submitted:
            email_norm = email.strip().lower()
            if not EMAIL_RE.match(email_norm):
                st.error("Introduce un email válido")
            else:
                result = http_login(email_norm, password)
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
                        save_session(token, email_norm)
                        go()

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
                        go()


if __name__ == "__main__":
    pass

