# --- Path bootstrap (asegura que la raíz del repo esté en sys.path) ---
import os, sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
STREAMLIT_DIR = THIS_DIR
if os.path.basename(STREAMLIT_DIR) != "streamlit_app":
    STREAMLIT_DIR = os.path.dirname(STREAMLIT_DIR)
ROOT_DIR = os.path.dirname(STREAMLIT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# ----------------------------------------------------------------------

import re
from pathlib import Path

import requests
import streamlit as st

from streamlit_app.auth_client import ensure_authenticated, save_token, current_token
from streamlit_app.components.ui import render_whatsapp_fab

from streamlit_app.utils.constants import (
    BRAND,
    LEADS_PAGE_PATH,
    ASSISTANT_PAGE_PATH,
)
from streamlit_app.utils.nav import go  # nav se importa del submódulo, no del paquete raíz
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.http_client import post
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.plan_utils import (
    resolve_user_plan,
    tiene_suscripcion_activa,
    subscription_cta,
)
from streamlit_app.cache_utils import cached_get


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PAGES = {
    "assistant": ASSISTANT_PAGE_PATH,
    "busqueda": LEADS_PAGE_PATH,
    "nichos": "pages/3_Mis_Nichos.py",
    "tareas": "pages/4_Tareas.py",
    "export": "pages/5_Exportaciones.py",
    "cuenta": "pages/8_Mi_Cuenta.py",
}


def page_exists(file: str) -> bool:
    return Path(file).exists()


BACKEND_URL = os.getenv("BACKEND_URL", http_client.BASE_URL)

auth = ensure_authenticated()
if auth:
    st.set_page_config(page_title=f"{BRAND} — Inicio", layout="wide")
else:
    st.set_page_config(page_title=f"{BRAND} — Accede a tu cuenta", layout="wide")

st.markdown(
    """
<style>
:root { --radius: 16px; --shadow: 0 6px 24px rgba(0,0,0,.08); }
.block-container{max-width:1100px;padding-top:2rem;}
.hero { padding: 8px 0 14px 0; }
.hero-title { font-size: 1.8rem; margin-bottom: .25rem; }
.hero-subtitle { font-size: 1.05rem; opacity:.9; margin-top:-.25rem; }
.card { background: white; border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); border: 1px solid rgba(0,0,0,.06); }
.card + .card { margin-top: 12px; }
.grid { display: grid; gap: 12px; }
.grid-4 { grid-template-columns: repeat(4, minmax(0,1fr)); }
@media (max-width: 1200px){ .grid-4 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px){ .grid-4 { grid-template-columns: 1fr; } }
.stButton>button { border-radius: 12px; padding: 10px 14px; border: 1px solid rgba(0,0,0,.08); }
.stButton>button:hover { border-color: rgba(0,0,0,.2); }
.card:empty { display: none; }
/* Evita que algún overlay o pseudo-elemento tape el botón */
.card { position: relative; }
.card * { position: relative; }
</style>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown("### ✨ Opensells")
    st.markdown(
        '<div class="hero-subtitle">Genera y gestiona leads de forma simple.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

if auth:
    token = current_token() or ""
    plan_info = resolve_user_plan(token)
    plan = plan_info["plan"]
    suscripcion_activa = tiene_suscripcion_activa(plan)
    nichos_resp = cached_get("/mis_nichos", token) if token else {}
    nichos = nichos_resp.get("nichos", []) if isinstance(nichos_resp, dict) else []
    num_nichos = len(nichos)
    tareas_resp = cached_get("tareas_pendientes", token) if token else []
    if isinstance(tareas_resp, dict):
        tareas = tareas_resp.get("tareas", [])
    else:
        tareas = tareas_resp or []
    num_tareas = len(tareas)

    with st.sidebar:
        logout_button()
        st.markdown("---")
        st.markdown(f"**Plan:** {plan}")

    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🗨️ Modo Asistente Virtual (beta)")
            st.write(
                "Chat interactivo que permite buscar leads, gestionar tareas, notas y estados."
            )
            if st.button("🗨️ Asistente Virtual", use_container_width=True):
                st.session_state["_nav_to"] = PAGES["assistant"]
            if not suscripcion_activa:
                subscription_cta()
            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📊 Modo Clásico")
            st.write(
                "Navegación por las páginas actuales: búsqueda, nichos, tareas y exportaciones."
            )
            if st.button("🔎 Búsqueda de Leads", use_container_width=True):
                st.session_state["_nav_to"] = PAGES["busqueda"]
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    items = [
        ("📂 Mis Nichos", "nichos"),
        ("📋 Tareas", "tareas"),
        ("📤 Exportaciones", "export"),
        ("⚙️ Mi Cuenta", "cuenta"),
    ]
    st.markdown('<div class="grid grid-4">', unsafe_allow_html=True)
    for label, key in items:
        page_file = PAGES.get(key)
        if page_file and page_exists(page_file):
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write(f"**{label}**")
                if st.button(label, use_container_width=True):
                    st.session_state["_nav_to"] = page_file
                st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Resumen de tu actividad"):
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Nichos", num_nichos)
        with m2:
            st.metric("Tareas pendientes", num_tareas)
        st.write(f"**Número de nichos:** {num_nichos}")
        st.write(f"**Número de tareas pendientes:** {num_tareas}")
        if not suscripcion_activa:
            subscription_cta()
else:
    tabs = st.tabs(["Entrar", "Crear cuenta"])
    with tabs[0]:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="tucorreo@ejemplo.com")
                password = st.text_input("Contraseña", type="password")
                submitted = st.form_submit_button("Iniciar sesión", use_container_width=True)

                # Separador visual pequeño
                st.caption(" ")

                # Desplegable: ¿Olvidaste tu contraseña?
                with st.expander("¿Olvidaste tu contraseña?", expanded=False):
                    st.write(
                        "Si olvidaste tu contraseña, por favor **envía un email a** "
                        "[opensellscontact@gmail.com]"
                        "(mailto:opensellscontact@gmail.com?subject=Solicitud%20de%20cambio%20de%20contrase%C3%B1a)"
                        " **solicitando el cambio de contraseña** desde el mismo correo con el que te registraste."
                    )
                    # Recomendación de contenido del email
                    st.markdown(
                        "- Tu **correo de registro**.\n"
                        "- Opcional: una breve nota confirmando que autorizas el cambio.\n"
                        "- Asunto sugerido: `Solicitud de cambio de contraseña`."
                    )
                    st.link_button(
                        "📧 Enviar email ahora",
                        "mailto:opensellscontact@gmail.com?subject=Solicitud%20de%20cambio%20de%20contrase%C3%B1a",
                        use_container_width=False,
                    )
            if submitted:
                email_norm = email.strip().lower()
                if not EMAIL_RE.match(email_norm):
                    st.error("Introduce un email válido")
                else:
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/login",
                            json={"email": email_norm, "password": password},
                            timeout=15,
                        )
                    except Exception as exc:
                        st.error(f"No se pudo conectar al backend: {exc}")
                    else:
                        if resp.status_code == 200:
                            token_payload = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
                            token_val = token_payload.get("access_token") if isinstance(token_payload, dict) else None
                            if token_val:
                                save_token(token_val)
                                st.session_state["auth_email"] = email_norm
                                st.success("Sesión iniciada")
                                st.experimental_rerun()
                            else:
                                st.error("Respuesta inválida del servidor (sin token).")
                        elif resp.status_code == 401:
                            st.error("Credenciales incorrectas.")
                        else:
                            st.error(f"Error al iniciar sesión: {resp.status_code}")
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
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
                    try:
                        login_resp = requests.post(
                            f"{BACKEND_URL}/login",
                            json={"email": email, "password": password_reg},
                            timeout=15,
                        )
                    except Exception as exc:
                        st.error(f"Error al iniciar sesión automáticamente: {exc}")
                    else:
                        if login_resp.status_code == 200:
                            login_payload = (
                                login_resp.json()
                                if login_resp.headers.get("Content-Type", "").startswith("application/json")
                                else {}
                            )
                            token_val = login_payload.get("access_token") if isinstance(login_payload, dict) else None
                            if token_val:
                                save_token(token_val)
                                st.session_state["auth_email"] = email
                                st.success("Sesión iniciada")
                                st.experimental_rerun()
                            else:
                                st.error("No se recibió token de acceso.")
                        else:
                            st.error("Error al iniciar sesión automáticamente.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# ---- Navegación fuera de callbacks ----
_target = st.session_state.pop("_nav_to", None)
if _target:
    go(_target)
    try:
        st.rerun()
    except Exception:
        pass
    st.stop()


if __name__ == "__main__":
    pass


render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")

