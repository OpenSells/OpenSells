import streamlit as st
from .http_client import get


def render_quota_badge():
    data = get("/mi_plan")
    plan = data.get("plan", "free")
    limits = data.get("limits", {})
    usage = data.get("usage", {})

    st.sidebar.markdown(f"**Plan:** {plan}")

    if plan == "free":
        fs = usage.get("free_searches", {})
        st.sidebar.progress(min(fs.get("used", 0) / (limits.get("searches_per_month") or 1), 1.0))
    else:
        lc = usage.get("lead_credits", {})
        if limits.get("lead_credits_month"):
            st.sidebar.progress(min(lc.get("used", 0) / limits["lead_credits_month"], 1.0))

    ai = usage.get("ai_messages", {})
    st.sidebar.write(
        f"IA hoy: {ai.get('used_today',0)}/{limits.get('ai_daily_limit',0)}"
    )
