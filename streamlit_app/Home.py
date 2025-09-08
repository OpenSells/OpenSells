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
from streamlit_app.utils.nav import go  # nav se importa del submódulo, no del paquete raíz
from streamlit_app.utils.http_client import post, login as http_login
from streamlit_app.utils.auth_utils import (
    is_authenticated,
    save_session,
    restore_session_if_allowed,
)
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.plan_utils import (
    obtener_plan,
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


restore_session_if_allowed()

auth = is_authenticated()
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
    token = st.session_state.get("auth_token", "")
    plan = obtener_plan(token)
    suscripcion_activa = tiene_suscripcion_activa(plan)
    nichos_resp = cached_get("mis_nichos", token) if token else {}
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
            st.markdown("</div>", unsafe_allow_html=True)


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

