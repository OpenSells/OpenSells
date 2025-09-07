"""Utility package for the Streamlit frontend."""

# Exportaciones robustas con fallbacks para evitar ImportError

from .style_utils import full_width_button
from . import http_client

try:  # pragma: no cover - defensa ante despliegues parciales
    from .constants import (
        BRAND,
        AFTER_LOGIN_PAGE_LABEL,
        AFTER_LOGIN_PAGE_PATH,
        LEADS_PAGE_LABEL,
        LEADS_PAGE_PATH,
        ASSISTANT_PAGE_LABEL,
        ASSISTANT_PAGE_PATH,
        SECONDARY_PAGES,
    )
except Exception:  # pragma: no cover - fallback seguro
    import os

    BRAND = os.getenv("BRAND_NAME", "OpenSells")

    AFTER_LOGIN_PAGE_LABEL = os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
    AFTER_LOGIN_PAGE_PATH = os.getenv(
        "AFTER_LOGIN_PAGE_PATH", "pages/Buscar_leads.py"
    )

    LEADS_PAGE_LABEL = os.getenv("LEADS_PAGE_LABEL", "Buscar leads")
    LEADS_PAGE_PATH = os.getenv("LEADS_PAGE_PATH", "pages/Buscar_leads.py")

    ASSISTANT_PAGE_LABEL = os.getenv(
        "ASSISTANT_PAGE_LABEL", "Asistente virtual (beta)"
    )
    ASSISTANT_PAGE_PATH = os.getenv(
        "ASSISTANT_PAGE_PATH", "pages/Asistente_virtual.py"
    )

    SECONDARY_PAGES = []

__all__ = [
    "full_width_button",
    "http_client",
    "BRAND",
    "AFTER_LOGIN_PAGE_LABEL",
    "AFTER_LOGIN_PAGE_PATH",
    "LEADS_PAGE_LABEL",
    "LEADS_PAGE_PATH",
    "ASSISTANT_PAGE_LABEL",
    "ASSISTANT_PAGE_PATH",
    "SECONDARY_PAGES",
]

