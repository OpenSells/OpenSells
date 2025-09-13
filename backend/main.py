from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from urllib.parse import urlparse
import os

from backend.database import get_db
from backend.models import (
    HistorialExport,
    LeadEstado,
    LeadExtraido,
    LeadTarea,
    Usuario,
    UsuarioMemoria,
)
from backend.core.plans import get_plan_for_user
from backend.core.usage import _error
from backend.core.usage import (
    can_export_csv,
    can_start_search,
    can_use_ai,
    consume_csv_export,
    consume_free_search,
    consume_lead_credits,
    month_key,
    get_count,
    inc_count,
    tareas_usadas_mes,
    ia_mensajes_usados_mes,
    leads_extraidos_mes,
    consume_ai,
)
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")
from backend.auth import (
    get_current_user,
    hashear_password,
    verificar_password,
    crear_token,
)

app = FastAPI()

if os.getenv("ENV") == "dev":
    from backend.routers import debug

    app.include_router(debug.router)


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


@app.get("/me")
def me(usuario=Depends(get_current_user)):
    return {"id": usuario.id, "email": usuario.email, "plan": usuario.plan}


@app.get("/mi_plan")
def mi_plan(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    plan_name, plan = get_plan_for_user(usuario)
    mkey = month_key()

    degraded = False
    try:
        db.execute(text("SELECT 1 FROM usage_counters LIMIT 1"))
        leads_usados = leads_extraidos_mes(db, usuario.id)
        tareas_usadas = tareas_usadas_mes(db, usuario.id)
        ia_usados = ia_mensajes_usados_mes(db, usuario.id)
    except Exception as e:  # pragma: no cover - table missing
        logger.warning("usage_counters table missing or inaccessible: %s", e)
        db.rollback()
        degraded = True
        leads_usados = tareas_usadas = ia_usados = 0

    leads_totales = plan.lead_credits_month
    if leads_totales is not None:
        leads_restantes = max(leads_totales - leads_usados, 0)
    else:
        leads_restantes = None

    result = {
        "plan": plan_name,
        "leads_mensuales": leads_totales,
        "leads_usados_mes": leads_usados,
        "leads_restantes": leads_restantes,
        "ia_mensajes": plan.ia_mensajes,
        "ia_usados_mes": ia_usados,
        "ia_restantes": max(plan.ia_mensajes - ia_usados, 0),
        "tareas_max": plan.tareas_max,
        "tareas_usadas_mes": tareas_usadas,
        "tareas_restantes": max(plan.tareas_max - tareas_usadas, 0),
        "csv_exportacion": plan.csv_exportacion,
        "permite_notas": plan.permite_notas,
        "permite_tareas": plan.tareas_max > 0,
    }
    if degraded:
        result["meta"] = {"degraded": True, "reason": "usage_counters_missing"}
    return result


class MemoriaPayload(BaseModel):
    descripcion: str


@app.get("/mi_memoria")
def obtener_memoria(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(UsuarioMemoria, usuario.email_lower)
    return {"memoria": row.descripcion if row else ""}


@app.post("/mi_memoria")
def guardar_memoria(
    payload: MemoriaPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(UsuarioMemoria, usuario.email_lower)
    if row:
        row.descripcion = payload.descripcion
    else:
        row = UsuarioMemoria(email_lower=usuario.email_lower, descripcion=payload.descripcion)
        db.add(row)
    db.commit()
    return {"ok": True}


@app.get("/mis_nichos")
def mis_nichos(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(LeadExtraido.nicho, LeadExtraido.nicho_original)
        .filter(LeadExtraido.user_email_lower == usuario.email_lower)
        .distinct()
        .all()
    )
    return {"nichos": [{"nicho": n, "nicho_original": o} for n, o in rows]}




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
    plan_name, plan = get_plan_for_user(usuario)
    if plan.tareas_max <= 0:
        _error("tasks", plan_name, 0, 0, "Tu plan no incluye tareas.")
    usadas = tareas_usadas_mes(db, usuario.id)
    if usadas >= plan.tareas_max:
        _error(
            "tasks",
            plan_name,
            plan.tareas_max,
            0,
            f"Tu plan no permite crear más tareas este mes (límite: {plan.tareas_max}). Considera mejorar tu plan.",
        )
    tarea = LeadTarea(
        email=usuario.email,
        texto=payload.texto,
        dominio=payload.dominio,
        nicho=payload.nicho,
        user_email_lower=usuario.email_lower,
        completado=payload.completado,
    )
    db.add(tarea)
    inc_count(db, usuario.id, "tareas", month_key(), 1)
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
    plan_name, plan = get_plan_for_user(usuario)
    if not plan.csv_unlimited and (plan.csv_exports_per_month or 0) == 0:
        _error(
            "csv",
            plan_name,
            plan.csv_exports_per_month,
            0,
            "Tu plan no incluye exportación CSV.",
        )
    ok, remaining, _ = can_export_csv(db, usuario.id, plan_name)
    if not ok:
        _error(
            "csv",
            plan_name,
            plan.csv_exports_per_month,
            remaining,
            f"Tu plan no permite más exportaciones CSV este mes (límite: {plan.csv_exports_per_month}). Considera mejorar tu plan.",
        )
    registro = HistorialExport(user_email=usuario.email_lower, filename=payload.filename)
    db.add(registro)
    consume_csv_export(db, usuario.id, plan_name)
    db.commit()
    return {"ok": True}


class AIPayload(BaseModel):
    prompt: str


@app.post("/ia")
def ia_endpoint(payload: AIPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    plan_name, plan = get_plan_for_user(usuario)
    ok, remaining = can_use_ai(db, usuario.id, plan_name)
    if not ok:
        _error(
            "ai",
            plan_name,
            plan.ia_mensajes,
            remaining,
            f"Has alcanzado el límite de mensajes de IA de tu plan para este mes (límite: {plan.ia_mensajes}).",
        )

    # Simular la invocación a OpenAI; en producción se llamaría realmente
    prompt = (payload.prompt or "").strip()
    if not prompt:
        usage_log.info("[USAGE] skip_ia: no OpenAI call")
        return {"ok": False, "reason": "empty_prompt"}

    # Si llega aquí, consideramos que se invocó correctamente
    consume_ai(db, usuario.id, plan_name)

    return {"ok": True}


class LeadsPayload(BaseModel):
    nuevos: int
    duplicados: int = 0


@app.post("/buscar_leads")
def buscar_leads(payload: LeadsPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    plan_name, plan = get_plan_for_user(usuario)
    ok, remaining, cap = can_start_search(db, usuario.id, plan_name)
    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "limit_exceeded",
                "feature": "search",
                "plan": plan_name,
                "limit": plan.searches_per_month,
                "remaining": remaining,
                "message": "Límite de búsquedas alcanzado",
            },
        )

    truncated = False
    duplicates = payload.duplicados
    saved = payload.nuevos
    if plan.type == "free":
        if cap is not None and saved > cap:
            duplicates += saved - cap
            saved = cap
            truncated = True
        consume_free_search(db, usuario.id, plan_name)
        credits_remaining = None
    else:
        nuevos_unicos = payload.nuevos - payload.duplicados
        available = remaining if remaining is not None else nuevos_unicos
        if available < nuevos_unicos:
            duplicates += nuevos_unicos - available
            nuevos_unicos = available
            truncated = True
        consume_lead_credits(db, usuario.id, plan_name, nuevos_unicos)
        saved = nuevos_unicos
        credits_remaining = (remaining - nuevos_unicos) if remaining is not None else None

    db.commit()
    return {
        "saved": saved,
        "duplicates": duplicates,
        "truncated": truncated,
        "credits_remaining": credits_remaining,
    }


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
