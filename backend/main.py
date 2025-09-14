from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from urllib.parse import urlparse
import os

from backend.database import get_db
from backend.bootstrap import auto_bootstrap_schema
from backend.models import (
    HistorialExport,
    LeadEstado,
    LeadExtraido,
    LeadTarea,
    Usuario,
    UsuarioMemoria,
)
from backend.core.plan_service import PlanService
from backend.core.usage_helpers import (
    can_export_csv,
    can_use_ai,
    consume_csv_export,
    day_key,
    inc_count,
    register_ia_message,
)
from backend.services.usage import UsageCounterService
from backend.config.plans import PLAN_LIMITS
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


@app.on_event("startup")
def _startup():
    auto_bootstrap_schema()


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
    svc = PlanService(db)
    return svc.get_quotas(usuario)


@app.get("/plan/usage")
@app.get("/usage")
@app.get("/stats/usage")
@app.get("/me/usage")
def plan_usage(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    plan_name = (usuario.plan or "free").strip().lower()
    svc = UsageCounterService(db)
    period = svc.get_current_period_date()
    row = svc.get_or_create_usage(usuario.id, period)
    limits = PLAN_LIMITS.get(
        plan_name, {"leads_per_month": None, "searches_per_month": None}
    )
    counters = {"leads_used": row.leads_used, "searches_used": row.searches_used}
    remaining = {
        "leads": None
        if not limits.get("leads_per_month")
        else max(limits["leads_per_month"] - row.leads_used, 0),
        "searches": None
        if not limits.get("searches_per_month")
        else max(limits["searches_per_month"] - row.searches_used, 0),
    }
    return {
        "period_month": period.isoformat(),
        "plan": plan_name,
        "counters": counters,
        "limits": limits,
        "remaining": remaining,
    }


@app.get("/plan/limits")
@app.get("/limits")
def plan_limits(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan_name, _ = svc.get_effective_plan(usuario)
    limits = svc.get_limits(plan_name)
    return {"plan": plan_name, "limits": limits}


class BumpPayload(BaseModel):
    kind: str
    amount: int = 1


@app.post("/plan/usage/bump")
def plan_usage_bump(
    payload: BumpPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)
):
    svc = UsageCounterService(db)
    if payload.kind == "leads":
        row = svc.increment_leads(usuario.id, payload.amount)
    else:
        row = svc.increment_searches(usuario.id, payload.amount)
    db.commit()
    return {"leads_used": row.leads_used, "searches_used": row.searches_used}


@app.get("/plan/quotas")
def plan_quotas(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PlanService(db)
    return svc.get_quotas(usuario)


@app.get("/plan/subscription")
@app.get("/subscription/summary")
@app.get("/billing/summary")
@app.get("/stripe/subscription")
def plan_subscription(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan_name, _ = svc.get_effective_plan(usuario)
    return {"plan": plan_name, "stripe": None, "status": "disabled"}


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
    tipo: str = "general"
    texto: str
    fecha: str | None = None
    prioridad: str = "media"
    nicho: str | None = None
    dominio: str | None = None
    completado: bool = False


@app.post("/tareas", status_code=201)
def crear_tarea(
    payload: TareaPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = PlanService(db)
    quotas = svc.get_quotas(usuario)
    remaining = quotas["remaining"]["tasks_active"]
    if remaining is not None and remaining <= 0:
        logger.info(
            "quota_reject feature=tasks user_id=%s plan=%s limit=%s used=%s",
            usuario.id,
            quotas["plan"],
            quotas["limits"]["tasks_active_max"],
            quotas["limits"]["tasks_active_max"] - remaining,
        )
        raise HTTPException(
            status_code=422,
            detail="Tareas máximas alcanzadas para tu plan.",
        )
    try:
        tarea = LeadTarea(
            email=usuario.email,
            texto=payload.texto,
            dominio=payload.dominio,
            nicho=payload.nicho,
            user_email_lower=usuario.email_lower,
            completado=payload.completado,
            tipo=payload.tipo,
            fecha=payload.fecha,
            prioridad=payload.prioridad,
        )
        db.add(tarea)
        db.flush()
        UsageService(db).increment(usuario.id, "tasks", 1)
        db.commit()
        db.refresh(tarea)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear la tarea")
    logger.info(
        "task_created user=%s tipo=%s dominio=%s nicho=%s tarea_id=%s",
        usuario.email_lower,
        payload.tipo,
        payload.dominio,
        payload.nicho,
        tarea.id,
    )
    return {
        "id": tarea.id,
        "texto": tarea.texto,
        "tipo": tarea.tipo,
        "dominio": tarea.dominio,
        "nicho": tarea.nicho,
        "fecha": tarea.fecha,
        "prioridad": tarea.prioridad,
        "completado": tarea.completado,
    }


@app.get("/tareas")
def listar_tareas(
    tipo: str | None = None,
    nicho: str | None = None,
    dominio: str | None = None,
    solo_pendientes: bool = False,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(LeadTarea).filter(LeadTarea.user_email_lower == usuario.email_lower)
    if tipo:
        q = q.filter(LeadTarea.tipo == tipo)
    if nicho:
        q = q.filter(LeadTarea.nicho == nicho)
    if dominio:
        q = q.filter(LeadTarea.dominio == dominio)
    if solo_pendientes:
        q = q.filter(LeadTarea.completado == False)
    tareas = q.all()
    return {
        "tareas": [
            {
                "id": t.id,
                "texto": t.texto,
                "tipo": t.tipo,
                "nicho": t.nicho,
                "dominio": t.dominio,
                "fecha": t.fecha,
                "prioridad": t.prioridad,
                "completado": t.completado,
            }
            for t in tareas
        ]
    }


@app.post("/tarea_lead", status_code=201)
def crear_tarea_lead(
    payload: TareaPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.dict()
    data["tipo"] = "lead"
    return crear_tarea(TareaPayload(**data), usuario, db)


@app.get("/tareas_pendientes")
def tareas_pendientes(
    tipo: str | None = None,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return listar_tareas(tipo=tipo, solo_pendientes=True, usuario=usuario, db=db)


class ExportPayload(BaseModel):
    filename: str


@app.post("/exportar_csv")
def exportar_csv(
    payload: ExportPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = PlanService(db)
    plan_name, plan = svc.get_effective_plan(usuario)
    ok, remaining, _ = can_export_csv(db, usuario.id, plan_name)
    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "limit_exceeded",
                "feature": "csv",
                "plan": plan_name,
                "limit": plan.csv_exports_per_month,
                "remaining": remaining,
                "message": "Límite de exportaciones alcanzado",
            },
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
    svc = PlanService(db)
    plan_name, plan = svc.get_effective_plan(usuario)
    ok, remaining = can_use_ai(db, usuario.id, plan_name)
    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "limit_exceeded",
                "feature": "ai",
                "plan": plan_name,
                "limit": plan.ai_daily_limit,
                "remaining": remaining,
                "message": "Límite de IA alcanzado",
            },
        )

    # Simular la invocación a OpenAI; en producción se llamaría realmente
    prompt = (payload.prompt or "").strip()
    if not prompt:
        usage_log.info("[USAGE] skip_ia: no OpenAI call")
        return {"ok": False, "reason": "empty_prompt"}

    # Si llega aquí, consideramos que se invocó correctamente
    inc_count(db, usuario.id, "ai_messages", day_key(), 1)
    register_ia_message(db, usuario)

    return {"ok": True}


class LeadsPayload(BaseModel):
    nuevos: int
    duplicados: int = 0


@app.post("/buscar_leads")
def buscar_leads(payload: LeadsPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan_name, plan = svc.get_effective_plan(usuario)
    usage_svc = UsageCounterService(db)
    period = usage_svc.get_current_period_date()
    usage = usage_svc.get_or_create_usage(usuario.id, period)
    limits = PLAN_LIMITS.get(plan_name, {})

    truncated = False
    duplicates = payload.duplicados
    saved = payload.nuevos
    if plan_name == "free":
        limit = limits.get("searches_per_month")
        if limit is not None and usage.searches_used >= limit:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "quota_exceeded",
                    "plan": plan_name,
                    "limit_type": "searches_per_month",
                    "message": "Has alcanzado el límite mensual de búsquedas de tu plan.",
                },
            )
        cap = plan.leads_cap_per_search
        if cap is not None and saved > cap:
            duplicates += saved - cap
            saved = cap
            truncated = True
        usage_svc.increment_searches(usuario.id, 1)
        credits_remaining = None
    else:
        limit = limits.get("leads_per_month")
        nuevos_unicos = payload.nuevos - payload.duplicados
        if limit is not None and usage.leads_used >= limit:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "quota_exceeded",
                    "plan": plan_name,
                    "limit_type": "leads_per_month",
                    "message": "Has alcanzado el límite mensual de leads de tu plan.",
                },
            )
        available = (
            limit - usage.leads_used if limit is not None else nuevos_unicos
        )
        if available < nuevos_unicos:
            duplicates += nuevos_unicos - available
            nuevos_unicos = available
            truncated = True
        usage_svc.increment_leads(usuario.id, nuevos_unicos)
        saved = nuevos_unicos
        credits_remaining = (
            (limit - usage.leads_used - nuevos_unicos) if limit is not None else None
        )

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
