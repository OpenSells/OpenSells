from __future__ import annotations

import streamlit as st

from . import AFTER_LOGIN_PAGE_LABEL, AFTER_LOGIN_PAGE_PATH

# Importa opcionales si existen
try:  # pragma: no cover - defensa ante despliegues parciales
    from . import LEADS_PAGE_PATH, ASSISTANT_PAGE_PATH
except Exception:  # pragma: no cover - fallback seguro
    LEADS_PAGE_PATH = None
    ASSISTANT_PAGE_PATH = None

HOME_PAGE = (AFTER_LOGIN_PAGE_LABEL or "Home")
__all__ = ["go", "HOME_PAGE"]

_ALIASES = {
    "app": "Home", "app.py": "Home", "inicio": "Home", "home.py": "Home", "home": "Home",
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
    candidate = (target or HOME_PAGE or "").strip() or "Home"
    label = _ALIASES.get(candidate.lower(), candidate)
    if _try_switch(label):
        return
    for path in (
        f"pages/{label}.py",
        f"{label}.py",
        AFTER_LOGIN_PAGE_PATH,
        LEADS_PAGE_PATH,
        ASSISTANT_PAGE_PATH,
        candidate,
    ):
        if path and _try_switch(path):
            return
    st.toast("No se encontró la página de destino; recargando…")
    st.rerun()
