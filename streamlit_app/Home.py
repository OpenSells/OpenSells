import streamlit as st
from streamlit_app.utils.auth_utils import (
    get_session,
    login_with_email,
    register_user,
    logout,
)
from streamlit_app.utils.ui import inject_global_css, action_card

st.set_page_config(page_title="OpenSells", page_icon="🔎", layout="wide")
inject_global_css()

session = get_session()

col_l, col_r = st.columns([0.72, 0.28], vertical_alignment="center")
with col_l:
    st.markdown(
        """
    <div class="brand">
      <div class="brand-title">OpenSells</div>
      <div class="brand-subtitle">Genera, organiza y trabaja tus leads en minutos.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with col_r:
    st.markdown(
        '<div class="badge {}">{}</div>'.format(
            "badge-ok" if session else "badge-warn",
            "Sesión activa" if session else "No has iniciado sesión",
        ),
        unsafe_allow_html=True,
    )

st.markdown("<div class='spacer-16'></div>", unsafe_allow_html=True)

# --- Si no hay sesión: pestañas de login/registro
if not session:
    tabs = st.tabs(["🔐 Inicia sesión", "✨ Crea tu cuenta"])
    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="tu@empresa.com")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            if submit:
                ok, msg = login_with_email(email=email, password=password)
                if ok:
                    st.success("¡Bienvenido/a! Redirigiendo…")
                    st.rerun()
                else:
                    st.error(msg or "No se pudo iniciar sesión.")

    with tabs[1]:
        with st.form("register_form"):
            username = st.text_input("Nombre de usuario (visible)")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Contraseña", type="password")
            reg_btn = st.form_submit_button("Crear cuenta", use_container_width=True)
            if reg_btn:
                ok, msg = register_user(
                    username=username, email=reg_email, password=reg_password
                )
                if ok:
                    st.success("Cuenta creada. Ahora inicia sesión con tu email.")
                else:
                    st.error(msg or "No se pudo crear la cuenta.")
    st.stop()

# --- Con sesión iniciada: Acciones principales
st.markdown("### ¿Qué quieres hacer hoy?")
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    action_card(
        title="Búsqueda de leads",
        desc="Encuentra y guarda leads por nicho desde Google/Maps.",
        icon="🔎",
        page="pages/1_Busqueda.py",  # AJUSTADO A pages/1_Busqueda.py
        cta="Abrir búsqueda",
    )
with c2:
    action_card(
        title="Asistente virtual (beta)",
        desc="Haz preguntas y lanza búsquedas guiadas con IA.",
        icon="🤖",
        page="pages/2_Asistente_Virtual.py",  # AJUSTADO A pages/2_Asistente_Virtual.py
        cta="Abrir asistente",
    )
with c3:
    action_card(
        title="Mi cuenta",
        desc="Tu plan, datos básicos y preferencias.",
        icon="👤",
        page="pages/Mi_cuenta.py",
        cta="Ver mi cuenta",
    )

st.divider()
st.markdown("### Más herramientas")
t1, t2 = st.columns([1, 1])
with t1:
    action_card(
        title="Exportaciones",
        desc="Descarga CSV con filtros combinados.",
        icon="📤",
        page="pages/5_Exportaciones.py",  # AJUSTADO A pages/5_Exportaciones.py
        cta="Ir a Exportaciones",
    )
with t2:
    action_card(
        title="Tareas y notas",
        desc="Gestiona pendientes por lead y por nicho.",
        icon="🗂️",
        page="pages/4_Tareas.py",  # AJUSTADO A pages/4_Tareas.py
        cta="Ir a Tareas",
    )

st.markdown("<div class='spacer-8'></div>", unsafe_allow_html=True)
st.button("Cerrar sesión", on_click=logout, use_container_width=False)
