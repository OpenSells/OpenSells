# Exports robustos con defaults -> override por constants.py

from .style_utils import full_width_button
from . import http_client

import os as _os

# 1) Defaults seguros (siempre definidos)
BRAND = _os.getenv("BRAND_NAME", "OpenSells")

AFTER_LOGIN_PAGE_LABEL = _os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
AFTER_LOGIN_PAGE_PATH  = _os.getenv("AFTER_LOGIN_PAGE_PATH",  "pages/Buscar_leads.py")

LEADS_PAGE_LABEL = _os.getenv("LEADS_PAGE_LABEL", "Buscar leads")
LEADS_PAGE_PATH  = _os.getenv("LEADS_PAGE_PATH",  "pages/Buscar_leads.py")

ASSISTANT_PAGE_LABEL = _os.getenv("ASSISTANT_PAGE_LABEL", "Asistente virtual (beta)")
ASSISTANT_PAGE_PATH  = _os.getenv("ASSISTANT_PAGE_PATH",  "pages/Asistente_virtual.py")

SECONDARY_PAGES = []

# 2) Override con valores reales si constants.py existe
try:
    from . import constants as _c
    BRAND = getattr(_c, "BRAND", BRAND)

    AFTER_LOGIN_PAGE_LABEL = getattr(_c, "AFTER_LOGIN_PAGE_LABEL", AFTER_LOGIN_PAGE_LABEL)
    AFTER_LOGIN_PAGE_PATH  = getattr(_c, "AFTER_LOGIN_PAGE_PATH",  AFTER_LOGIN_PAGE_PATH)

    LEADS_PAGE_LABEL = getattr(_c, "LEADS_PAGE_LABEL", LEADS_PAGE_LABEL)
    LEADS_PAGE_PATH  = getattr(_c, "LEADS_PAGE_PATH",  LEADS_PAGE_PATH)

    ASSISTANT_PAGE_LABEL = getattr(_c, "ASSISTANT_PAGE_LABEL", ASSISTANT_PAGE_LABEL)
    ASSISTANT_PAGE_PATH  = getattr(_c, "ASSISTANT_PAGE_PATH",  ASSISTANT_PAGE_PATH)

    SECONDARY_PAGES = getattr(_c, "SECONDARY_PAGES", SECONDARY_PAGES)
except Exception:
    # si falla, mantenemos los defaults y no crasheamos
    pass

__all__ = [
    "full_width_button",
    "http_client",
    "BRAND",
    "AFTER_LOGIN_PAGE_LABEL", "AFTER_LOGIN_PAGE_PATH",
    "LEADS_PAGE_LABEL", "LEADS_PAGE_PATH",
    "ASSISTANT_PAGE_LABEL", "ASSISTANT_PAGE_PATH",
    "SECONDARY_PAGES",
]
