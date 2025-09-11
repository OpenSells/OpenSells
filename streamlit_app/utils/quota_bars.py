import types
import streamlit as st

from streamlit_app.plan_utils import subscription_cta
from streamlit_app.utils.auth_session import get_auth_token


@st.cache_data(ttl=15, hash_funcs={types.ModuleType: id})
def _fetch_plan(api_client, token: str):
    resp = api_client.get("/mi_plan")
    if isinstance(resp, dict):
        raise RuntimeError("error")
    return resp.json()


def render_quota_bars(api_client, *, place: str = "sidebar"):
    """Render quota bars for the current user.

    Returns the JSON payload from /mi_plan so that callers can
    optionally use it for additional logic (e.g., disabling buttons).
    """
    token = get_auth_token()
    if not token:
        return None
    try:
        data = _fetch_plan(api_client, token)
    except Exception:
        if place == "sidebar":
            container = st.sidebar
        else:
            container = st
        with container:
            st.warning("No se pudo cargar tu estado de plan. Reintenta.")
        return None

    plan = data.get("plan", "free")
    limits = data.get("limits", {})
    usage = data.get("usage", {})

    container = st.sidebar if place == "sidebar" else st

    def _bar(label: str, used: int, total: int | None, help_text: str | None = None):
        if total in (None, 0):
            return
        pct = used / total if total else 0
        container.progress(pct, text=f"{label}: {used}/{total}")
        if help_text:
            container.caption(help_text)

    with container:
        if st.button("Actualizar cuotas", key=f"refresh_quota_{place}"):
            _fetch_plan.clear()
            st.experimental_rerun()

        exhausted = False

        if plan == "free":
            fs = usage.get("free_searches", {})
            _bar(
                "Búsquedas del mes",
                fs.get("used", 0),
                limits.get("searches_per_month"),
                f"{limits.get('searches_per_month')}/mes · hasta {limits.get('leads_cap_per_search')} leads por búsqueda",
            )
            ce = usage.get("csv_exports", {})
            _bar(
                "Exportaciones del mes",
                ce.get("used", 0),
                limits.get("csv_exports_per_month"),
                f"{limits.get('csv_exports_per_month')}/mes · máx. {limits.get('csv_rows_cap_free')} filas",
            )
            if fs.get("remaining") == 0 or ce.get("remaining") == 0:
                exhausted = True
        else:
            lc = usage.get("lead_credits", {})
            _bar(
                "Créditos de lead del mes",
                lc.get("used", 0),
                limits.get("lead_credits_month"),
            )
            if lc.get("remaining") == 0:
                exhausted = True

        ai = usage.get("ai_messages", {})
        _bar(
            "IA hoy",
            ai.get("used_today", 0),
            limits.get("ai_daily_limit"),
            "límite diario",
        )
        if ai.get("remaining_today") == 0:
            container.info("Límite diario de IA alcanzado. Reintenta mañana.")
            exhausted = True

        tasks = usage.get("tasks_active", {})
        _bar(
            "Tareas activas",
            tasks.get("current", 0),
            tasks.get("limit"),
            "activas a la vez",
        )

        if exhausted and plan == "free":
            subscription_cta()
        elif exhausted:
            subscription_cta()

    return data
