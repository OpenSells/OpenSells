from __future__ import annotations

import streamlit as st

from . import (
    AFTER_LOGIN_PAGE_LABEL,
    AFTER_LOGIN_PAGE_PATH,
    LEADS_PAGE_LABEL,
    LEADS_PAGE_PATH,
    ASSISTANT_PAGE_LABEL,
    ASSISTANT_PAGE_PATH,
)

# Alias retrocompatible para código legacy:
HOME_PAGE = (AFTER_LOGIN_PAGE_LABEL or "Home")  # ej.: "Buscar leads"

__all__ = ["go", "HOME_PAGE"]

_ALIASES: dict[str, str] = {
    "app": "Home",
    "app.py": "Home",
    "inicio": "Home",
    "home.py": "Home",
    "home": "Home",
    "buscar": LEADS_PAGE_LABEL,
    "búsqueda": LEADS_PAGE_LABEL,
    "busqueda": LEADS_PAGE_LABEL,
    "leads": LEADS_PAGE_LABEL,
    "buscar leads": LEADS_PAGE_LABEL,
    "asistente": ASSISTANT_PAGE_LABEL,
    "assistant": ASSISTANT_PAGE_LABEL,
    "ai": ASSISTANT_PAGE_LABEL,
    "asistente virtual": ASSISTANT_PAGE_LABEL,
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
    Si target es None, usa HOME_PAGE (alias de AFTER_LOGIN_PAGE_LABEL).
    Hace fallbacks inteligentes sin romper la app.
    """
    candidate = (target or HOME_PAGE or "").strip() or "Home"

    # 1) Intento por alias/label
    label = _ALIASES.get(candidate.lower(), candidate)
    if _try_switch(label):
        return

    # 2) Intento por rutas probables + fallback por env
    for path in (
        f"pages/{label}.py",
        f"{label}.py",
        AFTER_LOGIN_PAGE_PATH,
        LEADS_PAGE_PATH,
        ASSISTANT_PAGE_PATH,
        candidate,  # por si ya era ruta válida
    ):
        if path and _try_switch(path):
            return

    # 3) Último recurso: no dejar la app rota
    st.toast("No se encontró la página de destino; recargando…")
    st.rerun()
