import os

# existing constant
BRAND = os.getenv("BRAND_NAME", "OpenSells")

# new navigation constants
AFTER_LOGIN_PAGE_LABEL = os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
# Alternative direct path (used if label fails)
AFTER_LOGIN_PAGE_PATH = os.getenv(
    "AFTER_LOGIN_PAGE_PATH", "pages/Buscar_leads.py"
)

__all__ = ["BRAND", "AFTER_LOGIN_PAGE_LABEL", "AFTER_LOGIN_PAGE_PATH"]
