import os
import logging
from fastapi import Header, HTTPException, Request

logger = logging.getLogger("backend.search")


def guard_assistant_extraction(request: Request, x_client_source: str | None = Header(default=None)):
    """Bloquea extracción desde el asistente si está deshabilitada."""
    enabled = os.getenv("ASSISTANT_EXTRACTION_ENABLED", "false").lower() == "true"
    if x_client_source == "assistant" and not enabled:
        logger.info("blocked assistant extraction (flag=disabled, path=%s)", request.url.path)
        raise HTTPException(status_code=200, detail="assistant_extraction_placeholder")
