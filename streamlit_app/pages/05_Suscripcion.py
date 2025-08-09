# 05_Suscripcion.py – Página de planes y suscripción

import os, streamlit as st
import requests

from session_bootstrap import bootstrap
bootstrap()

from auth_utils import ensure_token_and_user, logout_button
from plan_utils import obtener_plan, force_redirect

BACKEND_URL = (
    st.secrets.get("BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or "https://opensells.onrender.com"
)

st.set_page_config(page_title="💳 Suscripción", page_icon="💳")
logout_button()
ensure_token_and_user()

price_free = st.secrets.get("STRIPE_PRICE_GRATIS") or os.getenv("STRIPE_PRICE_GRATIS")
price_basico = st.secrets.get("STRIPE_PRICE_BASICO") or os.getenv("STRIPE_PRICE_BASICO")
price_premium = st.secrets.get("STRIPE_PRICE_PREMIUM") or os.getenv("STRIPE_PRICE_PREMIUM")

plan = obtener_plan(st.session_state.get("token", ""))

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
