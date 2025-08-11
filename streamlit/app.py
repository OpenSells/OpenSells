"""Main entry point for the Streamlit app."""

import os
import streamlit as st
from session_bootstrap import bootstrap

bootstrap()
from auth_utils import ensure_token_and_user, logout_button

st.set_page_config(page_title="OpenSells — tu motor de prospección y leads", page_icon="🧩")
logout_button()
ensure_token_and_user()

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

suscription_page = "pages/6_Suscripcion.py"
suscription_icon = "💳"
if not os.path.exists(suscription_page):
    suscription_page = "pages/7_Mi_Cuenta.py"
    suscription_icon = "⚙️"

try:
    st.page_link("pages/2_Busqueda.py", label="Buscar leads ahora", icon="🔎")
    st.page_link("pages/3_Mis_Nichos.py", label="Ver mis nichos", icon="📂")
    st.page_link(suscription_page, label="Activar suscripción", icon=suscription_icon)
except AttributeError:
    try:
        st.link_button("🔎 Buscar leads ahora", "pages/2_Busqueda.py")
        st.link_button("📁 Ver mis nichos", "pages/3_Mis_Nichos.py")
        st.link_button("💳 Activar suscripción", suscription_page)
    except AttributeError:
        if st.button("🔎 Buscar leads ahora"):
            try:
                st.switch_page("pages/2_Busqueda.py")
            except Exception:
                pass
        if st.button("📁 Ver mis nichos"):
            try:
                st.switch_page("pages/3_Mis_Nichos.py")
            except Exception:
                pass
        if st.button("💳 Activar suscripción"):
            try:
                st.switch_page(suscription_page)
            except Exception:
                pass
