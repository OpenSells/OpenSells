from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from backend.auth import get_current_user
from backend.database import get_db
from backend.core.usage import inc_count, month_key

router = APIRouter()

@router.post("/debug/incrementar_uso")
def debug_increment(metric: str = "mensajes_ia", n: int = 1, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    if os.getenv("ENV") != "dev":
        raise HTTPException(status_code=403, detail="Not allowed")
    inc_count(db, usuario.id, metric, month_key(), n)
    return {"ok": True}
