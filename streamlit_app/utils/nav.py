from __future__ import annotations

import streamlit as st

from . import AFTER_LOGIN_PAGE_LABEL, AFTER_LOGIN_PAGE_PATH

# Alias retrocompatible para código legacy:
HOME_PAGE = (AFTER_LOGIN_PAGE_LABEL or "Home")  # ej.: "Buscar leads"

__all__ = ["go", "HOME_PAGE"]

_ALIASES: dict[str, str] = {
    "app": "Home",
    "app.py": "Home",
    "inicio": "Home",
    "home.py": "Home",
    "home": "Home",
    "buscar": "Buscar leads",
    "búsqueda": "Buscar leads",
    "busqueda": "Buscar leads",
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
        candidate,  # por si ya era ruta válida
    ):
        if path and _try_switch(path):
            return

    # 3) Último recurso: no dejar la app rota
    st.toast("No se encontró la página de destino; recargando…")
    st.rerun()
