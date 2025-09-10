from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from urllib.parse import urlparse
from datetime import datetime

from backend.database import get_db
from backend.models import (
    HistorialExport,
    LeadEstado,
    LeadTarea,
    Usuario,
    UserUsageMonthly,
)
from backend.auth import (
    get_current_user,
    hashear_password,
    verificar_password,
    crear_token,
)

app = FastAPI()

PLAN_LIMITS = {
    "free": {"tareas": 2, "csv_exports": 1},
    "basico": {"tareas": 5, "csv_exports": 5},
    "premium": {"tareas": 999, "csv_exports": 999},
}


def normalizar_dominio(dominio: str) -> str:
    if dominio.startswith("http://") or dominio.startswith("https://"):
        dominio = urlparse(dominio).netloc
    return dominio.replace("www.", "").strip().lower()


@app.get("/health")
def health():
    return {"status": "ok"}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email_lower = payload.email.lower()
    exists = db.query(Usuario).filter(func.lower(Usuario.email) == email_lower).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    user = Usuario(email=email_lower, hashed_password=hashear_password(payload.password))
    db.add(user)
    db.commit()
    return {"id": user.id}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email_lower = payload.email.lower()
    user = db.query(Usuario).filter(func.lower(Usuario.email) == email_lower).first()
    if not user or not verificar_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = crear_token({"sub": user.email})
    return {"access_token": token}


def _get_usage(db: Session, user_id: int) -> UserUsageMonthly:
    period = datetime.utcnow().strftime("%Y%m")
    usage = (
        db.query(UserUsageMonthly)
        .filter_by(user_id=user_id, period_yyyymm=period)
        .first()
    )
    if not usage:
        usage = UserUsageMonthly(user_id=user_id, period_yyyymm=period)
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


class TareaPayload(BaseModel):
    texto: str
    dominio: str | None = None
    nicho: str | None = None
    completado: bool = False


@app.post("/tareas")
def crear_tarea(
    payload: TareaPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limits = PLAN_LIMITS.get(usuario.plan, PLAN_LIMITS["free"])
    usage = _get_usage(db, usuario.id)
    if usage.tasks >= limits["tareas"]:
        raise HTTPException(status_code=403, detail="Límite de tareas excedido")
    tarea = LeadTarea(
        email=usuario.email,
        texto=payload.texto,
        dominio=payload.dominio,
        nicho=payload.nicho,
        user_email_lower=usuario.email_lower,
        completado=payload.completado,
    )
    db.add(tarea)
    usage.tasks += 1
    db.commit()
    db.refresh(tarea)
    return {"id": tarea.id, "texto": tarea.texto}


@app.get("/tareas")
def listar_tareas(
    completado: bool | None = None,
    nicho: str | None = None,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(LeadTarea).filter(LeadTarea.user_email_lower == usuario.email_lower)
    if completado is not None:
        q = q.filter(LeadTarea.completado == completado)
    if nicho:
        q = q.filter(LeadTarea.nicho == nicho)
    tareas = q.all()
    return {
        "tareas": [
            {
                "id": t.id,
                "texto": t.texto,
                "completado": t.completado,
                "nicho": t.nicho,
            }
            for t in tareas
        ]
    }


class ExportPayload(BaseModel):
    filename: str


@app.post("/exportar_csv")
def exportar_csv(
    payload: ExportPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limits = PLAN_LIMITS.get(usuario.plan, PLAN_LIMITS["free"])
    usage = _get_usage(db, usuario.id)
    if usage.csv_exports >= limits["csv_exports"]:
        raise HTTPException(status_code=403, detail="Límite de exportaciones excedido")
    registro = HistorialExport(user_email=usuario.email_lower, filename=payload.filename)
    db.add(registro)
    usage.csv_exports += 1
    db.commit()
    return {"ok": True}


@app.get("/historial")
def ver_historial(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(HistorialExport)
        .filter(HistorialExport.user_email == usuario.email_lower)
        .order_by(HistorialExport.timestamp.desc())
        .all()
    )
    return {
        "historial": [
            {"filename": r.filename, "timestamp": r.timestamp.isoformat() if r.timestamp else None}
            for r in rows
        ]
    }


class EstadoDominioRequest(BaseModel):
    dominio: str
    estado: str


@app.post("/estado_lead")
def guardar_estado(
    payload: EstadoDominioRequest,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dominio = normalizar_dominio(payload.dominio)
    stmt = (
        insert(LeadEstado)
        .values(user_email_lower=usuario.email_lower, dominio=dominio, estado=payload.estado)
        .on_conflict_do_update(
            index_elements=[LeadEstado.user_email_lower, LeadEstado.dominio],
            set_={"estado": payload.estado, "timestamp": func.now()},
        )
    )
    db.execute(stmt)
    db.commit()
    return {"mensaje": "Estado actualizado"}


@app.get("/estado_lead")
def obtener_estado(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    dominio = normalizar_dominio(dominio)
    row = (
        db.query(LeadEstado)
        .filter(LeadEstado.user_email_lower == usuario.email_lower, LeadEstado.dominio == dominio)
        .first()
    )
    return {"estado": row.estado if row else "nuevo"}
