import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def render_plan_usage(plan_name: str, quotas: dict, usage: dict):
    """Muestra un expander compacto con el uso del plan actual."""
    with st.expander("Tu plan y uso (click para ver)"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Plan actual:** {plan_name}")
        with col2:
            estado = usage.get("estado") or "activo"
            st.markdown(f"**Estado:** {estado}")

        st.markdown("---")
        for k in sorted(quotas.keys()):
            cuota = quotas.get(k)
            usado = usage.get(k, 0)
            if cuota and isinstance(cuota, int) and cuota > 0:
                st.progress(min(usado / cuota, 1.0))
                st.markdown(f"- **{k}**: {usado} / {cuota}")
            else:
                st.markdown(f"- **{k}**: {usado} (sin límite declarado)")


@st.cache_data(ttl=60)
def fetch_plan_and_usage(auth_token: str) -> tuple[str, dict, dict]:
    """Devuelve (plan_name, quotas, usage) desde el backend."""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    plan_name = "Free"
    usage: dict = {}
    quotas: dict = {}

    r_me = requests.get(f"{BACKEND_URL}/me", headers=headers, timeout=10)
    if r_me.ok:
        data = r_me.json()
        plan_name = data.get("plan") or plan_name
        usage["estado"] = "suspendido" if data.get("suspendido") else "activo"

    r_usage = requests.get(f"{BACKEND_URL}/plan/usage", headers=headers, timeout=10)
    if r_usage.ok:
        usage.update(r_usage.json())

    r_quotas = requests.get(f"{BACKEND_URL}/plan/quotas", headers=headers, timeout=10)
    if r_quotas.ok:
        quotas.update(r_quotas.json())

    return plan_name, quotas, usage
