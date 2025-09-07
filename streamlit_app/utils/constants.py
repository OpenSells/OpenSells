"""Centralized constants for the Streamlit frontend.

All values can be overridden via environment variables to keep the
configuration flexible across deployments. Every path points by default to a
file within ``streamlit_app/pages``.
"""

from __future__ import annotations

import os


# Nombre de la marca que se muestra en la interfaz.
BRAND = os.getenv("BRAND_NAME", "OpenSells")


# Datos de navegación principales de la aplicación.
LEADS_PAGE_LABEL = os.getenv("LEADS_PAGE_LABEL", "Búsqueda de leads")
LEADS_PAGE_PATH = os.getenv("LEADS_PAGE_PATH", "pages/1_Busqueda.py")

ASSISTANT_PAGE_LABEL = os.getenv(
    "ASSISTANT_PAGE_LABEL", "Asistente virtual (beta)"
)
ASSISTANT_PAGE_PATH = os.getenv(
    "ASSISTANT_PAGE_PATH", "pages/2_Asistente_Virtual.py"
)


# Página a la que se redirige tras un login satisfactorio.
AFTER_LOGIN_PAGE_LABEL = os.getenv(
    "AFTER_LOGIN_PAGE_LABEL", LEADS_PAGE_LABEL
)
AFTER_LOGIN_PAGE_PATH = os.getenv(
    "AFTER_LOGIN_PAGE_PATH", LEADS_PAGE_PATH
)


# Accesos secundarios opcionales mostrados en la página principal.
# El formato es una lista de tuplas: (label, path, descripción, emoji).
# Mantener la lista vacía por defecto y dejar ejemplos comentados para futuras
# extensiones.
SECONDARY_PAGES: list[tuple[str, str, str, str]] = [
    # ("Nichos", "pages/3_Mis_Nichos.py", "Gestiona y explora nichos y leads.", "🗂️"),
    # (
    #     "Tareas pendientes",
    #     "pages/4_Tareas.py",
    #     "Prioriza y marca tareas.",
    #     "✅",
    # ),
    # (
    #     "Exportaciones",
    #     "pages/5_Exportaciones.py",
    #     "Descarga CSV filtrados.",
    #     "📤",
    # ),
    # ("Emails", "pages/6_Emails.py", "Gestiona envíos de correos.", "✉️"),
    # ("Suscripción", "pages/7_Suscripcion.py", "Gestiona tu plan.", "💳"),
    # (
    #     "Mi cuenta / Configuración",
    #     "pages/8_Mi_Cuenta.py",
    #     "Preferencias y sesión.",
    #     "⚙️",
    # ),
]


__all__ = [
    "BRAND",
    "LEADS_PAGE_LABEL",
    "LEADS_PAGE_PATH",
    "ASSISTANT_PAGE_LABEL",
    "ASSISTANT_PAGE_PATH",
    "AFTER_LOGIN_PAGE_LABEL",
    "AFTER_LOGIN_PAGE_PATH",
    "SECONDARY_PAGES",
]

