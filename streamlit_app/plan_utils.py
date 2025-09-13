"""Utilidades relacionadas con los planes y sus límites."""

from __future__ import annotations

import time
import streamlit as st

from streamlit_app.cache_utils import cached_get
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components

DEFAULT_PLAN = {
    "plan": "free",
    "leads_mensuales": 40,
    "leads_usados_mes": 0,
    "leads_restantes": 40,
    "ia_mensajes": 5,
    "ia_usados_mes": 0,
    "ia_restantes": 5,
    "tareas_max": 4,
    "tareas_usadas_mes": 0,
    "tareas_restantes": 4,
    "csv_exportacion": False,
    "permite_notas": False,
    "permite_tareas": True,
}

PLAN_CACHE = {"free": DEFAULT_PLAN}


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


def resolve_user_plan(token: str) -> dict:
    """Obtiene el plan y límites desde el backend."""
    try:
        data = cached_get("/mi_plan", token, nocache_key=time.time())
        if data and data.get("plan"):
            PLAN_CACHE[data["plan"]] = data
            return data
    except Exception:
        pass
    return DEFAULT_PLAN


def tiene_suscripcion_activa(plan: str) -> bool:
    """Indica si el plan permite funciones avanzadas."""
    return plan != "free"


def puede_gestionar_tareas(mi_plan: dict) -> bool:
    return bool(mi_plan.get("permite_tareas", int(mi_plan.get("tareas_max", 0)) > 0))


def tareas_restantes(mi_plan: dict) -> int:
    return max(
        0,
        int(mi_plan.get("tareas_max", 0)) - int(mi_plan.get("tareas_usadas_mes", 0)),
    )


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


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
        (
            """
        <script>
        (function(){{
          try{{ window.top.location.href = "{url}"; }}catch(e){{}}
          setTimeout(function(){{
            try{{ window.top.location.href = "{url}"; }}catch(e){{}}
          }}, 80);
        })();
        </script>
        """
        ).format(url=url),
        height=0,
    )
    st.stop()


__all__ = [
    "resolve_user_plan",
    "tiene_suscripcion_activa",
    "puede_gestionar_tareas",
    "tareas_restantes",
    "subscription_cta",
    "force_redirect",
]
