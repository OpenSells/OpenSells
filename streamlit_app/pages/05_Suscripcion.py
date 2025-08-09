# 05_Suscripcion.py – Página de planes y suscripción

import os, streamlit as st
import requests
from auth_utils import ensure_token_and_user, logout_button
from plan_utils import obtener_plan
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components


def _force_redirect(url: str):
    st.success("Redirigiendo a Stripe...")
    st.link_button("👉 Abrir enlace si no se abre automáticamente", url, use_container_width=True)
    st.session_state['_redir_nonce'] = st.session_state.get('_redir_nonce', 0) + 1
    try:
        streamlit_js_eval(
            js_expressions=f'window.top.location.href="{url}"',
            key=f"jsredir_{st.session_state.get('_redir_nonce', 0)}",
        )
    except Exception:
        pass
    components.html(
        f'''
        <script>
        (function() {{
            try {{ window.top.location.href = "{url}"; }} catch(e) {{}}
            setTimeout(function() {{ try {{ window.top.location.href = "{url}"; }} catch(e) {{}} }}, 50);
        }})();
        </script>
        ''',
        height=0,
    )
    st.stop()


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

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Gratis")
    st.markdown("- 40 leads/mes\n- 5 mensajes IA\n- Sin exportación CSV")
    st.button("Elegir Gratis", disabled=(plan == "free"))

with col2:
    st.subheader("Básico")
    st.markdown("- Todo lo del Gratis\n- 200 leads/mes\n- Exportación CSV")
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
                        _force_redirect(url)
                    else:
                        st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error("No se pudo iniciar la suscripción.")
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Falta configurar el price_id del plan Básico.")

with col3:
    st.subheader("Premium")
    st.markdown("- Todo lo del Básico\n- 600 leads/mes\n- Soporte prioritario")
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
                        _force_redirect(url)
                    else:
                        st.error("La respuesta no contiene URL de Stripe.")
                else:
                    st.error("No se pudo iniciar la suscripción.")
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Falta configurar el price_id del plan Premium.")

st.caption("El cobro se gestiona de forma segura en Stripe.")
