import requests
import streamlit as st


def render_quota_badge(api_url: str, token: str):
    """Fetch /mi_plan and render simple quota info."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        data = requests.get(f"{api_url}/mi_plan", headers=headers, timeout=5).json()
    except Exception:
        st.warning("No se pudo obtener la información del plan")
        return
    plan = data.get("plan")
    usage = data.get("usage", {})
    st.caption(f"Plan: {plan}")
    lead = usage.get("lead_credits", {})
    if lead.get("remaining") is not None:
        total = lead["used"] + lead["remaining"]
        pct = lead["used"] / total if total else 0
        st.progress(pct, text=f"Créditos usados: {lead.get('used',0)}")
    ai = usage.get("ai_messages", {})
    st.caption(f"IA hoy: {ai.get('used_today',0)}/{ai.get('remaining_today',0)+ai.get('used_today',0)}")
