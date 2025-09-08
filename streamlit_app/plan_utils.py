"""Utilidades relacionadas con los planes y sus límites.

Este módulo se comparte entre distintas páginas de Streamlit.  Resuelve el
plan y los límites consultando al backend mediante ``/mi_plan`` y ofrece
helpers para mostrar un pequeño panel de consumo."""

from __future__ import annotations

import time
import streamlit as st
from streamlit_app.cache_utils import cached_get
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components

PLAN_ALIASES = {"free": "Free", "basico": "Pro", "premium": "Business"}


def resolve_user_plan(token: str) -> dict:
    """Devuelve la información del plan y consumo actual del usuario."""

    try:
        data = cached_get("mi_plan", token, nocache_key=time.time())
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {
        "plan": "free",
        "limits": {
            "leads_mensuales": 40,
            "ia_mensajes": 5,
            "tareas_max": 4,
            "csv_exportacion": False,
        },
        "usage": {"leads": 0, "ia_msgs": 0, "tasks": 0, "csv_exports": 0},
    }


def obtener_plan(token: str) -> str:
    """Compatibilidad con código existente."""

    return resolve_user_plan(token).get("plan", "free")


def tiene_suscripcion_activa(plan: str) -> bool:
    return plan != "free"


def render_plan_panel(info: dict) -> None:
    plan = info.get("plan", "free")
    alias = PLAN_ALIASES.get(plan, plan)
    limits = info.get("limits", {})
    usage = info.get("usage", {})
    st.markdown(f"**Plan:** {alias}")
    st.caption(
        f"Leads {usage.get('leads',0)}/{limits.get('leads_mensuales') or '∞'} · "
        f"IA {usage.get('ia_msgs',0)}/{limits.get('ia_mensajes') or '∞'} · "
        f"Tareas {usage.get('tasks',0)}/{limits.get('tareas_max') or '∞'}"
    )


def subscription_cta():
    if hasattr(st, "page_link"):
        st.page_link("pages/7_Suscripcion.py", label="💳 Ver planes y suscribirme")
    else:
        st.markdown("💳 [Ver planes y suscribirme](./07_Suscripcion)")


def force_redirect(url: str) -> None:
    if not url:
        return
    st.link_button("👉 Abrir enlace si no se abre automáticamente", url, use_container_width=True)
    st.session_state["_redir_nonce"] = st.session_state.get("_redir_nonce", 0) + 1
    try:
        streamlit_js_eval(
            js_expressions=f'window.top.location.href="{url}"',
            key=f"jsredir_{st.session_state['_redir_nonce']}",
        )
    except Exception:
        pass
    components.html(
        f"""
        <script>
        (function(){{
          try{{ window.top.location.href = "{url}"; }}catch(e){{}}
          setTimeout(function(){{
            try{{ window.top.location.href = "{url}"; }}catch(e){{}}
          }}, 80);
        }})();
        </script>
        """,
        height=0,
    )
    st.stop()


__all__ = [
    "PLAN_ALIASES",
    "resolve_user_plan",
    "obtener_plan",
    "tiene_suscripcion_activa",
    "render_plan_panel",
    "subscription_cta",
    "force_redirect",
]
