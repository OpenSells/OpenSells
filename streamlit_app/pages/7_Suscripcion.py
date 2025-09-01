# 7_Suscripcion.py – Página de planes y suscripción

import os
import os
import streamlit as st
import requests
from dotenv import load_dotenv

from streamlit_app.utils.auth_utils import (
    rehydrate_session,
    clear_session,
    get_token,
    get_user,
)
from streamlit_app.utils.auth_guard import require_auth_or_render_home_login
from streamlit_app.utils import http_client
from streamlit_app.plan_utils import force_redirect
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils.plans import PLANS_FEATURES

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

rehydrate_session()
if not require_auth_or_render_home_login():
    st.stop()
st.session_state["last_path"] = "pages/7_Suscripcion.py"
token = get_token()
user = get_user()

if st.sidebar.button("Cerrar sesión"):
    clear_session()
    st.rerun()

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
