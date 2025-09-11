import types
from typing import Any, Dict

import streamlit as st

from streamlit_app.plan_utils import subscription_cta
from streamlit_app.utils.auth_session import get_auth_token


@st.cache_data(ttl=15, hash_funcs={types.ModuleType: id})
def _fetch_plan(api_client) -> Dict[str, Any]:
    resp = api_client.get("/mi_plan")
    if hasattr(resp, "status_code"):
        if resp.status_code != 200:
            raise RuntimeError(f"/mi_plan {resp.status_code}")
        try:
            return resp.json()
        except Exception as e:  # pragma: no cover - network errors
            raise RuntimeError(f"/mi_plan invalid JSON: {e}")
    if isinstance(resp, dict):
        return resp
    raise RuntimeError("Unexpected /mi_plan response type.")


def render_quota_bars(api_client, *, place: str = "sidebar"):
    """Render quota bars for the current user and return the /mi_plan payload."""

    token = get_auth_token()
    if not token:
        return None
    try:
        data = _fetch_plan(api_client)
    except Exception as e:  # pragma: no cover - network errors
        ctx = st.sidebar if place == "sidebar" else st.container()
        with ctx:
            st.warning("No se pudo cargar tu estado de plan. Reintenta.")
            st.caption(f"Detalle técnico: {e}")
        return None

    plan = data.get("plan", "free")
    limits = data.get("limits", {})
    usage = data.get("usage", {})

    ctx = st.sidebar if place == "sidebar" else st.container()
    with ctx:
        if st.button("Actualizar cuotas", key=f"refresh_quota_{place}"):
            _fetch_plan.clear()
            st.experimental_rerun()

        exhausted = False

        def _bar(label: str, used: int, total: int | None, help_text: str | None = None):
            if total in (None, 0):
                return
            pct = used / total if total else 0
            st.progress(min(pct, 1.0), text=f"{label}: {used}/{total}")
            if help_text:
                st.caption(help_text)

        if plan == "free":
            fs = usage.get("free_searches", {})
            used = int(fs.get("used", 0))
            total = int(limits.get("searches_per_month") or 0)
            _bar(
                "Búsquedas del mes",
                used,
                total,
                f"{total}/mes · hasta {limits.get('leads_cap_per_search', 0)} leads por búsqueda",
            )
            ce = usage.get("csv_exports", {})
            csv_used = int(ce.get("used", 0))
            csv_total = int(limits.get("csv_exports_per_month") or 0)
            _bar(
                "Exportaciones del mes",
                csv_used,
                csv_total,
                f"{csv_total}/mes · máx. {limits.get('csv_rows_cap_free', 0)} filas",
            )
            if fs.get("remaining") == 0 or ce.get("remaining") == 0:
                exhausted = True
        else:
            lc = usage.get("lead_credits", {})
            used = int(lc.get("used", 0))
            total = int(limits.get("lead_credits_month") or 0)
            _bar("Créditos de lead del mes", used, total)
            if lc.get("remaining") == 0 and total:
                exhausted = True

        ai = usage.get("ai_messages", {})
        ai_used = int(ai.get("used_today", 0))
        ai_total = int(limits.get("ai_daily_limit") or 0)
        _bar("IA hoy", ai_used, ai_total, "límite diario")
        if ai.get("remaining_today") == 0 and ai_total:
            st.info("Límite diario de IA alcanzado. Reintenta mañana.")
            exhausted = True

        tasks = usage.get("tasks_active", {})
        cur = int(tasks.get("current", 0))
        lim = int(tasks.get("limit") or limits.get("tasks_active_max") or 0)
        _bar("Tareas activas", cur, lim, "activas a la vez")

        if exhausted:
            subscription_cta()

    return data
