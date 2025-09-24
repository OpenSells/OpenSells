"""Main entry point for the Streamlit app."""

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

import logging
import streamlit as st
from sqlalchemy.engine import make_url

from streamlit_app.auth_client import ensure_authenticated, clear_token
from streamlit_app.components.ui import render_whatsapp_fab
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils.nav import HOME_PAGE, go

init_cookie_manager_mount()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    url = make_url(DATABASE_URL)
    masked_dsn = (
        f"{url.drivername}://***:***@{url.host}:{url.port}/{url.database}"
        + ("?" + "&".join(f"{k}={v}" for k, v in url.query.items()) if url.query else "")
    )
    logging.info("Streamlit DB → %s", masked_dsn)

st.set_page_config(page_title="OpenSells — tu motor de prospección y leads", page_icon="🧩")

if not ensure_authenticated():
    go(HOME_PAGE)
    st.stop()

user = st.session_state.get("user") or st.session_state.get("me")
if user:
    st.session_state["user"] = user

if st.sidebar.button("Cerrar sesión"):
    clear_token()
    go(HOME_PAGE)
    st.experimental_rerun()

st.title("OpenSells — tu motor de prospección y leads")
st.markdown(
    """
### Bienvenido a OpenSells
**Tu motor de prospección y leads** para captar clientes desde la web y Google Maps, con IA para enriquecer, clasificar y priorizar.

**Beneficios:**
- Consigue más leads de calidad en menos tiempo.
- Centraliza tu prospección: busca, guarda, clasifica y actúa.
- Evita duplicados entre nichos y mejora el foco de tu equipo.
- Escala con planes flexibles y paga solo por lo que usas.

**Qué hace OpenSells:**
- Extracción de leads desde Web y Google Maps (+ IA para enriquecer).
- Control de duplicados por dominio y aviso si ya existe en otros nichos.
- Gestión de nichos, tareas y notas por lead.
- Exportaciones CSV con filtros combinables (dominio, nicho, estado).
- Buscador global de leads.
- Planes con Stripe y control de acceso por plan (free, básico, premium).
- Backend FastAPI + PostgreSQL; Frontend Streamlit.

**Qué puedes hacer ahora mismo:**
"""
)

suscription_page = "pages/7_Suscripcion.py"
suscription_icon = "💳"
if not os.path.exists(suscription_page):
    suscription_page = "pages/8_Mi_Cuenta.py"
    suscription_icon = "⚙️"

try:
    st.page_link("pages/1_Busqueda.py", label="Buscar leads ahora", icon="🔎")
    st.page_link("pages/3_Mis_Nichos.py", label="Ver mis nichos", icon="📂")
    st.page_link(suscription_page, label="Activar suscripción", icon=suscription_icon)
except AttributeError:
    try:
        st.link_button("🔎 Buscar leads ahora", "pages/1_Busqueda.py")
        st.link_button("📁 Ver mis nichos", "pages/3_Mis_Nichos.py")
        st.link_button("💳 Activar suscripción", suscription_page)
    except AttributeError:
        if st.button("🔎 Buscar leads ahora"):
            go("pages/1_Busqueda.py")
        if st.button("📁 Ver mis nichos"):
            go("pages/3_Mis_Nichos.py")
        if st.button("💳 Activar suscripción"):
            go(suscription_page)

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")
