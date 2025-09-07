from __future__ import annotations

import streamlit as st

# Import directo desde constants: evita import circular
from .constants import (
    AFTER_LOGIN_PAGE_LABEL,
    AFTER_LOGIN_PAGE_PATH,
    LEADS_PAGE_PATH,
    ASSISTANT_PAGE_PATH,
)

HOME_PAGE = AFTER_LOGIN_PAGE_LABEL or "Home"
__all__ = ["go", "HOME_PAGE"]

_ALIASES: dict[str, str] = {
    "app": "Home", "app.py": "Home", "home": "Home", "inicio": "Home",
    "leads": "Buscar leads", "buscar leads": "Buscar leads",
    "asistente": "Asistente virtual (beta)", "assistant": "Asistente virtual (beta)",
    "ai": "Asistente virtual (beta)", "asistente virtual": "Asistente virtual (beta)",
}


def _try_switch(target: str) -> bool:
    try:
        st.switch_page(target)
        return True
    except Exception:
        return False


def go(target: str | None = None) -> None:
    """
    Navega por label (preferente) o por ruta.
    Si target es None, usa HOME_PAGE.
    """
    candidate = (target or HOME_PAGE or "").strip() or "Home"
    # 1) Intento por alias/label
    label = _ALIASES.get(candidate.lower(), candidate)
    if _try_switch(label):
        return
    # 2) Rutas probables + fallbacks
    for path in (
        f"pages/{label}.py",
        f"{label}.py",
        AFTER_LOGIN_PAGE_PATH,
        LEADS_PAGE_PATH,
        ASSISTANT_PAGE_PATH,
        candidate,  # por si ya era una ruta válida
    ):
        if path and _try_switch(path):
            return
    # 3) Último recurso: no dejes la app rota
    st.toast("No se encontró la página de destino; recargando…")
    st.rerun()

