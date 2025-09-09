import streamlit as st

# Intenta reutilizar el helper existente del proyecto.
# Preferencia: resolve_user_plan() / obtener_plan() / http_client.get("/mi_plan") si existe.
def _fetch_plan_summary(http_client):
    """
    Devuelve dict normalizado:
    {
      "label": "Free|Pro|Business",
      "leads_used": int, "leads_limit": int|None,
      "ia_used": int,     "ia_limit": int|None,
      "tasks_used": int,  "tasks_limit": int|None,
    }
    """
    # 1) Si existe /mi_plan, úsalo
    try:
        data = http_client.get("/mi_plan")
        plan_key = data.get("plan") or data.get("plan_key") or "free"
        label = {"free":"Free","basico":"Pro","premium":"Business"}.get(plan_key, plan_key.title())
        limits = data.get("limits", {})
        used   = data.get("used", {}) or data.get("usage", {})

        def _fmt_lim(k):
            v = limits.get(k, None)
            return None if v in (None, "None") else int(v)

        return {
            "label": label,
            "leads_used": int(used.get("leads", 0)),   "leads_limit": _fmt_lim("leads_mensuales"),
            "ia_used":    int(used.get("ia_msgs", 0)), "ia_limit":    _fmt_lim("ia_mensajes"),
            "tasks_used": int(used.get("tasks", 0)),   "tasks_limit": _fmt_lim("tareas_max"),
        }
    except Exception:
        pass

    # 2) Fallback: usar /me o helpers existentes
    try:
        me = http_client.get("/me")
        plan_key = (me.get("plan") or me.get("user", {}).get("plan") or "free").lower()
        label = {"free":"Free","basico":"Pro","premium":"Business"}.get(plan_key, plan_key.title())
    except Exception:
        label = "Free"

    # Si no hay contadores, muestra 0/valores por defecto
    return {
        "label": label,
        "leads_used": 0, "leads_limit": 40 if label=="Free" else (200 if label=="Pro" else 600),
        "ia_used": 0,    "ia_limit":    5 if label=="Free" else (50 if label=="Pro" else None),
        "tasks_used": 0, "tasks_limit":  4 if label=="Free" else None,
    }

def render_sidebar_plan(http_client):
    # Llamar SIEMPRE después de cualquier otro contenido de la sidebar,
    # para que quede al final.
    data = _fetch_plan_summary(http_client)

    def _fmt_pair(used, limit):
        if limit is None:
            return f"{used}/∞"
        return f"{used}/{limit}"

    with st.sidebar:
        st.divider()
        st.markdown(f"**Plan:** {data['label']}")
        st.caption(
            f"Leads {_fmt_pair(data['leads_used'], data['leads_limit'])} · "
            f"IA {_fmt_pair(data['ia_used'], data['ia_limit'])} · "
            f"Tareas {_fmt_pair(data['tasks_used'], data['tasks_limit'])}"
        )
