import os

BRAND = os.getenv("BRAND_NAME", "OpenSells")

AFTER_LOGIN_PAGE_LABEL = os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
AFTER_LOGIN_PAGE_PATH = os.getenv("AFTER_LOGIN_PAGE_PATH", "pages/Buscar_leads.py")

LEADS_PAGE_LABEL = os.getenv("LEADS_PAGE_LABEL", "Buscar leads")
LEADS_PAGE_PATH = os.getenv("LEADS_PAGE_PATH", "pages/Buscar_leads.py")

ASSISTANT_PAGE_LABEL = os.getenv(
    "ASSISTANT_PAGE_LABEL", "Asistente virtual (beta)"
)
ASSISTANT_PAGE_PATH = os.getenv(
    "ASSISTANT_PAGE_PATH", "pages/Asistente_virtual.py"
)

# Lista de accesos secundarios: (label, path, descripcion, emoji)
SECONDARY_PAGES = [
    (
        "Nichos",
        "pages/Nichos.py",
        "Gestiona y elimina nichos; explora sus leads.",
        "🗂️",
    ),
    (
        "Tareas pendientes",
        "pages/Tareas_pendientes.py",
        "Crea, prioriza y marca tareas por lead.",
        "✅",
    ),
    (
        "Historial",
        "pages/Historial.py",
        "Revisa acciones recientes por lead y nicho.",
        "🕓",
    ),
    (
        "Exportaciones",
        "pages/Exportaciones.py",
        "Descarga CSV filtrados y combinados.",
        "📤",
    ),
    (
        "Mi cuenta / Configuración",
        "pages/Mi_cuenta.py",
        "Datos de usuario y preferencias.",
        "⚙️",
    ),
]

__all__ = [
    "BRAND",
    "AFTER_LOGIN_PAGE_LABEL",
    "AFTER_LOGIN_PAGE_PATH",
    "LEADS_PAGE_LABEL",
    "LEADS_PAGE_PATH",
    "ASSISTANT_PAGE_LABEL",
    "ASSISTANT_PAGE_PATH",
    "SECONDARY_PAGES",
]
