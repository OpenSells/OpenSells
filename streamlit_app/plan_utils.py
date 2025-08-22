"""Utilidades relacionadas con los planes y sus límites.

Este módulo se comparte entre distintas páginas de Streamlit.  Además de
recuperar el plan del usuario desde el backend, expone un diccionario con la
información de cada plan para que la interfaz pueda reaccionar según los
límites disponibles.
"""

from __future__ import annotations

import time
import streamlit as st

from streamlit_app.cache_utils import cached_get
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Definición de planes
# ---------------------------------------------------------------------------

PLANES = {
    "free": {
        "leads_mensuales": 40,
        "ia_mensajes": 5,
        "tareas_max": 4,
        "notas_permitidas": False,
        "csv_exportacion": False,
        "historial": True,
        "soporte": "email",
    },
    "basico": {
        "leads_mensuales": 200,
        "ia_mensajes": 50,
        "tareas_max": None,
        "notas_permitidas": True,
        "csv_exportacion": True,
        "historial": True,
        "soporte": "email_prioritario",
    },
    "premium": {
        "leads_mensuales": 600,
        "ia_mensajes": None,
        "tareas_max": None,
        "notas_permitidas": True,
        "csv_exportacion": True,
        "historial": True,
        "soporte": "whatsapp",
    },
}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------


def obtener_plan(token: str) -> str:
    """Devuelve el plan actual del usuario o ``free`` si no se puede determinar."""

    try:
        data = cached_get("mi_plan", token, nocache_key=time.time())
        if data:
            return (data.get("plan") or "free").strip().lower()
    except Exception:
        # En caso de error de red u otro, asumimos plan gratuito para no
        # bloquear al usuario.
        pass
    return "free"


def tiene_suscripcion_activa(plan: str) -> bool:
    """Indica si el plan permite funciones avanzadas."""

    return plan != "free"


def obtener_limite(plan: str, clave: str):
    """Obtiene el límite configurado para un recurso.

    Args:
        plan: nombre del plan (``free``, ``basico`` o ``premium``).
        clave: recurso a consultar, p.ej. ``"leads_mensuales"``.

    Returns:
        El valor configurado o ``None`` si el recurso es ilimitado.
    """

    return PLANES.get(plan, PLANES["free"]).get(clave)


def permite_recurso(plan: str, clave: str) -> bool:
    """Comprueba si el recurso indicado está habilitado para el plan.

    Esta función es útil para recursos booleanos como ``notas_permitidas`` o
    ``csv_exportacion``.
    """

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
    "PLANES",
    "obtener_plan",
    "tiene_suscripcion_activa",
    "obtener_limite",
    "permite_recurso",
    "subscription_cta",
    "force_redirect",
]

