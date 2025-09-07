# Exports robustos: defaults seguros + override desde constants.py.
import os as _os

# Defaults (siempre definidos)
BRAND = _os.getenv("BRAND_NAME", "OpenSells")

AFTER_LOGIN_PAGE_LABEL = _os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
AFTER_LOGIN_PAGE_PATH  = _os.getenv("AFTER_LOGIN_PAGE_PATH",  "pages/Buscar_leads.py")

LEADS_PAGE_LABEL = _os.getenv("LEADS_PAGE_LABEL", "Buscar leads")
LEADS_PAGE_PATH  = _os.getenv("LEADS_PAGE_PATH",  "pages/Buscar_leads.py")

ASSISTANT_PAGE_LABEL = _os.getenv("ASSISTANT_PAGE_LABEL", "Asistente virtual (beta)")
ASSISTANT_PAGE_PATH  = _os.getenv("ASSISTANT_PAGE_PATH", "pages/Asistente_virtual.py")

SECONDARY_PAGES = []

# Override si constants.py existe
try:
    from . import constants as _c

    def _ov(name, current):
        return getattr(_c, name, current)

    BRAND = _ov("BRAND", BRAND)
    AFTER_LOGIN_PAGE_LABEL = _ov("AFTER_LOGIN_PAGE_LABEL", AFTER_LOGIN_PAGE_LABEL)
    AFTER_LOGIN_PAGE_PATH  = _ov("AFTER_LOGIN_PAGE_PATH",  AFTER_LOGIN_PAGE_PATH)
    LEADS_PAGE_LABEL       = _ov("LEADS_PAGE_LABEL",       LEADS_PAGE_LABEL)
    LEADS_PAGE_PATH        = _ov("LEADS_PAGE_PATH",        LEADS_PAGE_PATH)
    ASSISTANT_PAGE_LABEL   = _ov("ASSISTANT_PAGE_LABEL",   ASSISTANT_PAGE_LABEL)
    ASSISTANT_PAGE_PATH    = _ov("ASSISTANT_PAGE_PATH",    ASSISTANT_PAGE_PATH)
    SECONDARY_PAGES        = _ov("SECONDARY_PAGES",        SECONDARY_PAGES)
except Exception:
    # mantenemos defaults sin romper arranque
    pass

__all__ = [
    "BRAND",
    "AFTER_LOGIN_PAGE_LABEL", "AFTER_LOGIN_PAGE_PATH",
    "LEADS_PAGE_LABEL", "LEADS_PAGE_PATH",
    "ASSISTANT_PAGE_LABEL", "ASSISTANT_PAGE_PATH",
    "SECONDARY_PAGES",
]

