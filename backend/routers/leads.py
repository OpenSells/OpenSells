from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import LeadExtraido
from backend.auth import get_current_user

router = APIRouter()

class EstadoPayload(BaseModel):
    estado_contacto: constr(strip_whitespace=True, to_lower=True)

@router.patch("/leads/{lead_id}/estado_contacto")
def actualizar_estado_contacto(
    lead_id: int,
    payload: EstadoPayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    allowed = {"pendiente", "contactado", "cerrado", "fallido"}
    if payload.estado_contacto not in allowed:
        raise HTTPException(status_code=422, detail="estado_contacto inválido")
    lead = db.get(LeadExtraido, lead_id)
    if not lead or lead.user_email_lower != user.email_lower:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    lead.estado_contacto = payload.estado_contacto
    db.commit()
    db.refresh(lead)
    return {"id": lead.id, "estado_contacto": lead.estado_contacto}
