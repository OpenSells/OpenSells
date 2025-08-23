import os
from typing import Optional, List

from streamlit_app.utils import http_client

EXTRAER_LEADS_MSG = (
    "🚧 Esta funcionalidad desde el asistente estará disponible próximamente. "
    "Mientras tanto, puedes usar la página de Búsqueda para generar leads."
)

ASSISTANT_EXTRACTION_ENABLED = os.getenv("ASSISTANT_EXTRACTION_ENABLED", "false").lower() == "true"


def _placeholder():
    return {"error": EXTRAER_LEADS_MSG}


def api_buscar(cliente_ideal: str, forzar_variantes: bool = False, contexto_extra: Optional[str] = None, headers: dict | None = None):
    if not ASSISTANT_EXTRACTION_ENABLED:
        return _placeholder()
    payload = {"cliente_ideal": cliente_ideal, "forzar_variantes": forzar_variantes, "contexto_extra": contexto_extra}
    r = http_client.post("/buscar", json=payload, headers=headers)
    if r is not None and getattr(r, "status_code", None) == 200:
        return r.json()
    return _placeholder() if r is None else {"error": getattr(r, "text", "unknown"), "status": getattr(r, "status_code", 500)}


def api_buscar_variantes_seleccionadas(variantes: List[str], headers: dict | None = None):
    if not ASSISTANT_EXTRACTION_ENABLED:
        return _placeholder()
    r = http_client.post("/buscar_variantes_seleccionadas", json={"variantes": variantes}, headers=headers)
    if r is not None and getattr(r, "status_code", None) == 200:
        return r.json()
    return _placeholder() if r is None else {"error": getattr(r, "text", "unknown"), "status": getattr(r, "status_code", 500)}
