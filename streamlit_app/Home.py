import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import (
    BRAND,
    LEADS_PAGE_LABEL,
    ASSISTANT_PAGE_LABEL,
    SECONDARY_PAGES,
)
from utils.nav import go
from utils.http_client import post, login as http_login
from utils.auth_utils import (
    is_authenticated,
    save_session,
    restore_session_if_allowed,
)
from utils.logout_button import logout_button


def _go_leads():
    from utils.nav import go as _go

    _go(LEADS_PAGE_LABEL)


def _go_assistant():
    from utils.nav import go as _go

    _go(ASSISTANT_PAGE_LABEL)


def _go_pair(label, path=None):
    from utils.nav import go as _go

    try:
        _go(label)
    except Exception:
        if path:
            _go(path)


def _card_primary(title, desc, on_click):
    st.button(f"{title}\n{desc}", use_container_width=True, on_click=on_click)


def _card_secondary(emoji, title, desc, on_click):
    st.button(
        f"{emoji} {title}\n{desc}", use_container_width=True, on_click=on_click
    )


restore_session_if_allowed()

if is_authenticated():
    st.set_page_config(page_title=f"{BRAND} — Inicio", layout="wide")
else:
    st.set_page_config(page_title=f"{BRAND} — Accede a tu cuenta", layout="wide")

if is_authenticated():
    st.markdown(
        """
        <style>
        .card-container .stButton>button {
            border-radius:16px;
            box-shadow:0 6px 24px rgba(0,0,0,.06);
            padding:1.5rem;
            transition:all .1s ease-in-out;
            white-space:normal;
        }
        .card-container .stButton>button:hover {
            box-shadow:0 6px 24px rgba(0,0,0,.12);
            transform:translateY(-2px);
        }
        .primary-grid .stButton>button {font-size:1.25rem;}
        .secondary-grid .stButton>button {font-size:1.05rem;padding:1rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"# {BRAND}")
    cols_header = st.columns([3, 1])
    with cols_header[0]:
        st.subheader("¿Qué quieres hacer hoy?")
    with cols_header[1]:
        st.info("Sesión activa")

    st.markdown('<div class="card-container">', unsafe_allow_html=True)

    st.markdown('<div class="primary-grid">', unsafe_allow_html=True)
    cols = st.columns(2)
    with cols[0]:
        _card_primary(
            "🔎 Búsqueda de leads",
            "Encuentra y guarda leads por nicho desde Google/Maps.",
            _go_leads,
        )
    with cols[1]:
        _card_primary(
            "🤖 Asistente virtual (beta)",
            "Haz preguntas y lanza búsquedas guiadas con IA.",
            _go_assistant,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Más herramientas")
    st.markdown('<div class="secondary-grid">', unsafe_allow_html=True)
    sec_cols = st.columns(4)
    for i, (label, path, desc, emoji) in enumerate(SECONDARY_PAGES):
        col = sec_cols[i % len(sec_cols)]
        with col:
            _card_secondary(emoji, label, desc, lambda l=label, p=path: _go_pair(l, p))
    st.markdown("</div>", unsafe_allow_html=True)

    logout_button()
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(f"# {BRAND}")
    st.subheader("Accede a tu cuenta")

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
