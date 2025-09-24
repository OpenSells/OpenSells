# 7_Suscripcion.py – Página de planes y suscripción

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

import streamlit as st
import requests
from dotenv import load_dotenv

from streamlit_app.auth_client import (
    ensure_authenticated,
    current_token,
    auth_headers as auth_client_headers,
)
import streamlit_app.utils.http_client as http_client
from streamlit_app.plan_utils import force_redirect, resolve_user_plan
from streamlit_app.utils.plans import PLANS_FEATURES
from streamlit_app.utils.auth_session import remember_current_page
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.components.ui import render_whatsapp_fab

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

PAGE_NAME = "Suscripcion"
remember_current_page(PAGE_NAME)
if not ensure_authenticated():
    st.title(PAGE_NAME)
    st.warning("Sesión expirada. Vuelve a iniciar sesión.")
    st.stop()

token = current_token()
user = st.session_state.get("user") or st.session_state.get("me")
if user:
    st.session_state["user"] = user

with st.sidebar:
    logout_button()

price_free = _safe_secret("STRIPE_PRICE_GRATIS")
price_basico = _safe_secret("STRIPE_PRICE_BASICO")
price_premium = _safe_secret("STRIPE_PRICE_PREMIUM")

plan = resolve_user_plan(token)["plan"]


def _fetch_plan_features():
    try:
        r = http_client.get("/planes")
        if r is not None and r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return PLANS_FEATURES


plan_features = _fetch_plan_features()
st.title("💳 Suscripción")

plan_alias = {"free": "Free", "basico": "Pro", "premium": "Business"}
plan_actual = plan_alias.get(plan.lower(), plan).lower()
prices = {"Free": "0 €/mes", "Pro": "14,99 €/mes", "Business": "49,99 €/mes"}

cols = st.columns(len(plan_features))
for idx, (nombre, feats) in enumerate(plan_features.items()):
    with cols[idx]:
        st.subheader(f"{nombre} — {prices.get(nombre, '')}")
        if plan_actual == nombre.lower():
            st.caption("✅ Plan actual")
        for f in feats:
            st.markdown(f"- {f}")
        if nombre.lower() == "free":
            st.button("Elegir Gratis", disabled=(plan_actual == "free"))
        elif nombre.lower() == "pro":
            if st.button("Suscribirme al Pro"):
                if price_basico:
                    try:
                        r = requests.post(
                            f"{BACKEND_URL}/crear_portal_pago",
                            headers=auth_client_headers(),
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
                    st.error("Falta configurar el price_id del plan Pro.")
        elif nombre.lower() == "business":
            if st.button("Suscribirme al Business"):
                if price_premium:
                    try:
                        r = requests.post(
                            f"{BACKEND_URL}/crear_portal_pago",
                            headers=auth_client_headers(),
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
                    st.error("Falta configurar el price_id del plan Business.")

st.caption("El pago y la gestión se realizan en Stripe.")

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")
