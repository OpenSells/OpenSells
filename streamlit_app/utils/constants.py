import os

# Marca
BRAND = os.getenv("BRAND_NAME", "OpenSells")

# Navegación post-login por defecto
AFTER_LOGIN_PAGE_LABEL = os.getenv("AFTER_LOGIN_PAGE_LABEL", "Buscar leads")
AFTER_LOGIN_PAGE_PATH  = os.getenv("AFTER_LOGIN_PAGE_PATH",  "pages/Buscar_leads.py")

# Páginas principales de la Home
LEADS_PAGE_LABEL     = os.getenv("LEADS_PAGE_LABEL",     "Buscar leads")
LEADS_PAGE_PATH      = os.getenv("LEADS_PAGE_PATH",      "pages/Buscar_leads.py")

ASSISTANT_PAGE_LABEL = os.getenv("ASSISTANT_PAGE_LABEL", "Asistente virtual (beta)")
ASSISTANT_PAGE_PATH  = os.getenv("ASSISTANT_PAGE_PATH",  "pages/Asistente_virtual.py")

# Accesos secundarios (label, path, descripción, emoji)
SECONDARY_PAGES = [
    ("Nichos", "pages/Nichos.py", "Gestiona y explora nichos y leads.", "🗂️"),
    ("Tareas pendientes", "pages/Tareas_pendientes.py", "Prioriza y marca tareas.", "✅"),
    ("Historial", "pages/Historial.py", "Acciones recientes y cambios.", "🕓"),
    ("Exportaciones", "pages/Exportaciones.py", "Descarga CSV filtrados.", "📤"),
    ("Mi cuenta / Configuración", "pages/Mi_cuenta.py", "Preferencias y sesión.", "⚙️"),
]

