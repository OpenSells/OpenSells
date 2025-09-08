"""Utilidades relacionadas con los planes y sus límites.

Este módulo se comparte entre distintas páginas de Streamlit.  Recupera el
plan del usuario desde el backend y expone funciones auxiliares para que la
interfaz reaccione según los límites disponibles.
"""

from __future__ import annotations

import time
import streamlit as st

from streamlit_app.cache_utils import cached_get
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Límite por defecto y caché
# ---------------------------------------------------------------------------

DEFAULT_LIMITS = {
    "leads_por_mes": 40,
    "mensajes_ia_por_mes": 5,
    "tareas_max": 4,
    "permite_notas": False,
    "permite_export_csv": False,
    "soporte": "email",
}

PLAN_CACHE = {"free": DEFAULT_LIMITS}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------


def resolve_user_plan(token: str) -> dict:
    """Obtiene el plan y límites desde el backend."""

    try:
        data = cached_get("mi_plan", token, nocache_key=time.time())
        if data and "plan" in data:
            plan = (data.get("plan") or "free").strip().lower()
            limits = data.get("limits") or DEFAULT_LIMITS
            PLAN_CACHE[plan] = limits
            return {"plan": plan, "limits": limits}
    except Exception:
        pass
    return {"plan": "free", "limits": DEFAULT_LIMITS}


def tiene_suscripcion_activa(plan: str) -> bool:
    """Indica si el plan permite funciones avanzadas."""

    return plan != "free"


def obtener_limite(plan: str, clave: str):
    """Obtiene el límite configurado para un recurso."""

    return PLAN_CACHE.get(plan, PLAN_CACHE["free"]).get(clave)


def permite_recurso(plan: str, clave: str) -> bool:
    """Comprueba si el recurso indicado está habilitado para el plan."""

    valor = obtener_limite(plan, clave)
    return bool(valor)


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
    "resolve_user_plan",
    "tiene_suscripcion_activa",
    "obtener_limite",
    "permite_recurso",
    "subscription_cta",
    "force_redirect",
]
