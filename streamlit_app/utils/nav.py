"""Navigation utilities for Streamlit pages.

Provides a robust ``go`` function that can navigate using either page labels
or relative paths.  It also supports a set of common aliases so the caller can
use more human-friendly names.
"""

import streamlit as st

from . import AFTER_LOGIN_PAGE_LABEL, AFTER_LOGIN_PAGE_PATH

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
    """Try to switch to ``target`` and return whether it succeeded."""

    try:
        st.switch_page(target)
        return True
    except Exception:
        return False


def go(target: str | None = None) -> None:
    """Navigate by label (preferred) or relative path.

    If ``target`` is ``None`` it will default to
    ``AFTER_LOGIN_PAGE_LABEL`` or ``AFTER_LOGIN_PAGE_PATH``.
    """

    candidate = (target or AFTER_LOGIN_PAGE_LABEL or "").strip()
    if not candidate:
        candidate = "Home"

    # 1) Attempt via alias -> label
    label = _ALIASES.get(candidate.lower(), candidate)
    if _try_switch(label):
        return

    # 2) Attempt via most probable paths
    for path in (
        f"pages/{label}.py",
        f"{label}.py",
        AFTER_LOGIN_PAGE_PATH,
        candidate,  # in case it was already a valid path
    ):
        if path and _try_switch(path):
            return

    # 3) Last resort: don't break the app
    st.toast("No se encontró la página de destino; recargando…")
    st.rerun()


__all__ = ["go"]

