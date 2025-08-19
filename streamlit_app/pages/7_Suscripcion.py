# 7_Suscripcion.py – Página de planes y suscripción

import os
import streamlit as st
import requests
from dotenv import load_dotenv

from streamlit_app.utils.auth_utils import ensure_session, logout_and_redirect
from streamlit_app.utils import http_client
from streamlit_app.plan_utils import force_redirect
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount

init_cookie_manager_mount()

load_dotenv()


def _safe_secret(name: str, default=None):
    """Safely retrieve configuration from env or Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")

st.set_page_config(page_title="💳 Suscripción", page_icon="💳")


user, token = ensure_session(require_auth=True)

if st.sidebar.button("Cerrar sesión"):
    logout_and_redirect()

price_free = _safe_secret("STRIPE_PRICE_GRATIS")
price_basico = _safe_secret("STRIPE_PRICE_BASICO")
price_premium = _safe_secret("STRIPE_PRICE_PREMIUM")

plan = (user or {}).get("plan", "free")

st.title("💳 Suscripción")

cols = st.columns(3)

with cols[0]:
    st.subheader("Gratis — 0 €/mes")
    st.markdown(
        """
        • Buscar nichos, ver listado  
        • Exportación limitada  
        • Sin tareas avanzadas  
        """
    )
    st.button("Elegir Gratis", disabled=(plan == "free"))

with cols[1]:
    st.subheader("Básico — 14,99 €/mes")
    st.markdown(
        """
        • Extracción de leads normal  
        • Exportación CSV por nicho  
        • Tareas y notas básicas  
        """
    )
    if st.button("Suscribirme al Básico"):
        if price_basico:
            try:
                r = requests.post(
                    f"{BACKEND_URL}/crear_portal_pago",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    params={"plan": price_basico},
                    timeout=30,
                )
                if r.status_code == 200:
                    url = r.json().get("url")
                    if url:
                        force_redirect(url)
                    else:
                        st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error("No se pudo iniciar la suscripción.")
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Falta configurar el price_id del plan Básico.")

with cols[2]:
    st.subheader("Premium — 49,99 €/mes")
    st.markdown(
        """
        • Extracción ampliada y rápida  
        • Exportación global + filtros combinados  
        • Priorización de tareas, historial y asistente  
        """
    )
    if st.button("Suscribirme al Premium"):
        if price_premium:
            try:
                r = requests.post(
                    f"{BACKEND_URL}/crear_portal_pago",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    params={"plan": price_premium},
                    timeout=30,
                )
                if r.status_code == 200:
                    url = r.json().get("url")
                    if url:
                        force_redirect(url)
                    else:
                        st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error("No se pudo iniciar la suscripción.")
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Falta configurar el price_id del plan Premium.")

st.caption("El pago y la gestión se realizan en Stripe.")
