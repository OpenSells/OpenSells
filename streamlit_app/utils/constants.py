import os

BRAND = os.getenv("BRAND_NAME", "OpenSells")

AFTER_LOGIN_PAGE_LABEL = os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
AFTER_LOGIN_PAGE_PATH = os.getenv("AFTER_LOGIN_PAGE_PATH", "pages/Buscar_leads.py")

__all__ = ["BRAND", "AFTER_LOGIN_PAGE_LABEL", "AFTER_LOGIN_PAGE_PATH"]
