# 7_Suscripcion.py – Página de planes y suscripción

import os
import streamlit as st
import requests
from dotenv import load_dotenv

import streamlit_app.utils.http_client as http_client
from streamlit_app.plan_utils import force_redirect
from streamlit_app.utils.plans import PLANS_FEATURES
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.components.sidebar_plan import render_sidebar_plan

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
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

token = get_auth_token()
user = st.session_state.get("user")
if token and not user:
    resp_user = http_client.get("/me")
    if isinstance(resp_user, dict) and resp_user.get("_error") == "unauthorized":
        st.warning("Sesión expirada. Vuelve a iniciar sesión.")
        st.stop()
    if getattr(resp_user, "status_code", None) == 200:
        user = resp_user.json()
        st.session_state["user"] = user

with st.sidebar:
    logout_button()

render_sidebar_plan(http_client)

price_free = _safe_secret("STRIPE_PRICE_GRATIS")
price_basico = _safe_secret("STRIPE_PRICE_BASICO")
price_premium = _safe_secret("STRIPE_PRICE_PREMIUM")

plan = (user or {}).get("plan", "free")


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
                            headers={"Authorization": f"Bearer {token}"},
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
                            headers={"Authorization": f"Bearer {token}"},
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
