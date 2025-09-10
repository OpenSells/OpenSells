from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from urllib.parse import urlparse

from backend.database import get_db
from backend.models import (
    HistorialExport,
    LeadEstado,
    LeadExtraido,
    LeadTarea,
    Usuario,
    UsuarioMemoria,
)
from backend.core.plan_config import get_plan_for_user, get_limits
from backend.core import usage as usage_service
from backend.auth import (
    get_current_user,
    hashear_password,
    verificar_password,
    crear_token,
)

app = FastAPI()


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
    plan = get_plan_for_user(usuario)
    limits = get_limits(plan)
    month = usage_service.month_key()
    day = usage_service.day_key()

    usage = {
        "lead_credits": {
            "used": usage_service.get_count(db, usuario.id, "lead_credits", month),
            "remaining": (
                limits.lead_credits_month
                - usage_service.get_count(db, usuario.id, "lead_credits", month)
                if limits.lead_credits_month is not None
                else None
            ),
            "period": month,
        },
        "free_searches": {
            "used": usage_service.get_count(db, usuario.id, "free_searches", month),
            "remaining": (
                limits.searches_per_month
                - usage_service.get_count(db, usuario.id, "free_searches", month)
                if limits.searches_per_month is not None
                else None
            ),
            "period": month,
        },
        "csv_exports": {
            "used": usage_service.get_count(db, usuario.id, "csv_exports", month),
            "remaining": (
                limits.csv_exports_per_month
                - usage_service.get_count(db, usuario.id, "csv_exports", month)
                if limits.csv_exports_per_month is not None
                else None
            ),
            "period": month,
        },
        "ai_messages": {
            "used_today": usage_service.get_count(db, usuario.id, "ai_messages", day),
            "remaining_today": (
                limits.ai_daily_limit
                - usage_service.get_count(db, usuario.id, "ai_messages", day)
            ),
            "period": day,
        },
        "tasks_active": {
            "current": usage_service.count_active_tasks(db, usuario.email_lower),
            "limit": limits.tasks_active_max,
        },
    }

    return {"plan": plan, "limits": limits.dict(), "usage": usage}


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


class SearchPayload(BaseModel):
    leads: list[str]
    nicho: str | None = None


@app.post("/buscar_leads")
def buscar_leads(
    payload: SearchPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(usuario)
    ok, remaining, cap = usage_service.can_start_search(db, usuario.id, plan)
    limits = get_limits(plan)
    if plan == "free" and not ok:
        usage_service.limit_error(
            "search",
            plan,
            limits.searches_per_month or 0,
            remaining or 0,
            "Límite de búsquedas mensual alcanzado",
        )

    domains = [normalizar_dominio(d) for d in payload.leads]
    unique: list[str] = []
    for d in domains:
        if d not in unique:
            unique.append(d)

    existing = {
        row.dominio
        for row in db.query(LeadExtraido.dominio)
        .filter(
            LeadExtraido.user_email_lower == usuario.email_lower,
            LeadExtraido.dominio.in_(unique),
        )
        .all()
    }

    new_domains = [d for d in unique if d not in existing]
    duplicates = len(domains) - len(new_domains)
    truncated = False

    if plan == "free":
        cap = limits.leads_cap_per_search
        if len(new_domains) > cap:
            truncated = True
            new_domains = new_domains[:cap]
    else:
        remaining_credits = remaining
        if remaining_credits is not None and len(new_domains) > remaining_credits:
            truncated = True
            new_domains = new_domains[:remaining_credits]

    for d in new_domains:
        lead = LeadExtraido(
            user_email=usuario.email,
            user_email_lower=usuario.email_lower,
            dominio=d,
            url=d,
            nicho=payload.nicho or "",
            nicho_original=payload.nicho or "",
        )
        db.add(lead)
    db.commit()

    saved = len(new_domains)

    if plan == "free":
        usage_service.consume_free_search(db, usuario.id)
        credits_remaining = None
    else:
        usage_service.consume_lead_credits(db, usuario.id, saved)
        credits_remaining = remaining - saved if remaining is not None else None

    return {
        "saved": saved,
        "duplicates": duplicates,
        "truncated": truncated,
        "credits_remaining": credits_remaining,
    }




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
    plan = get_plan_for_user(usuario)
    limits = get_limits(plan)
    activos = (
        db.query(LeadTarea)
        .filter(LeadTarea.user_email_lower == usuario.email_lower, LeadTarea.completado == False)
        .count()
    )
    if activos >= limits.tasks_active_max:
        usage_service.limit_error(
            "tasks", plan, limits.tasks_active_max, 0, "Límite de tareas activas alcanzado"
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
    plan = get_plan_for_user(usuario)
    limits = get_limits(plan)
    ok, remaining, rows_cap = usage_service.can_export_csv(db, usuario.id, plan)
    if not ok:
        usage_service.limit_error(
            "csv", plan, limits.csv_exports_per_month or 0, remaining or 0, "Límite de exportaciones alcanzado"
        )
    registro = HistorialExport(user_email=usuario.email_lower, filename=payload.filename)
    db.add(registro)
    usage_service.consume_csv_export(db, usuario.id)
    db.commit()
    return {"ok": True, "rows_cap": rows_cap}


@app.post("/ia")
def ia_endpoint(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    plan = get_plan_for_user(usuario)
    limits = get_limits(plan)
    ok, remaining = usage_service.can_use_ai(db, usuario.id, plan)
    if not ok:
        usage_service.limit_error(
            "ai", plan, limits.ai_daily_limit, remaining, "Límite diario de IA alcanzado"
        )
    usage_service.consume_ai(db, usuario.id)
    return {"ok": True, "remaining": remaining - 1}


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
