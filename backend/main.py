# --- Standard library ---
import os
import logging
from urllib.parse import urlparse

# --- Third-party ---
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

# --- Local / project ---
from backend.database import engine, SessionLocal, DATABASE_URL, get_db
from backend.models import (
    Usuario,
    HistorialExport,
    LeadEstado,
    LeadExtraido,
    LeadTarea,
    UsuarioMemoria,
)
from backend.core.plan_service import PlanService
from backend.core.usage_helpers import (
    can_export_csv,
    can_start_search,
    can_use_ai,
    consume_csv_export,
    consume_free_search,
    consume_lead_credits,
    day_key,
    inc_count,
    register_ia_message,
)
from backend.core.usage_service import UsageService

# --- Load environment variables ---
load_dotenv()

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")
logger.info("CODE_MARKER tasks/stability %s", __file__)
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


# ---- MODELOS DE ENTRADA ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---- ENDPOINTS AUTH ----
@app.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.strip()
    email_lower = email.lower()

    # Comprobar por columna normalizada (evita problemas de mayúsculas)
    exists = db.query(Usuario.id).filter(Usuario.user_email_lower == email_lower).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    # Crear usuario rellenando SIEMPRE user_email_lower
    user = Usuario(
        email=email,
        user_email_lower=email_lower,
        hashed_password=hashear_password(payload.password),
        plan="free",
        suspendido=False,
    )

    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email ya registrado")

    return {"id": user.id}


@app.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email_lower = payload.email.lower()
    # Puedes dejar tu filtro actual con func.lower(Usuario.email) si prefieres.
    # Recomendado (consistente con el registro y más eficiente):
    user = db.query(Usuario).filter(Usuario.user_email_lower == email_lower).first()

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
    svc = PlanService(db)
    quotas = svc.get_quotas(usuario)
    return {"plan": quotas["plan"], "usage": quotas["usage"]}


@app.get("/plan/limits")
@app.get("/limits")
def plan_limits(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan_name, _ = svc.get_effective_plan(usuario)
    limits = svc.get_limits(plan_name)
    return {"plan": plan_name, "limits": limits}


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




class TareaCreate(BaseModel):
    texto: str
    tipo: Literal["general", "nicho", "lead"]
    dominio: Optional[str] = None
    nicho: Optional[str] = None
    prioridad: Optional[Literal["alta", "media", "baja"]] = "media"
    fecha: Optional[date] = None
    completado: bool = False

    @staticmethod
    def _extract_value(value: Any):
        if isinstance(value, dict):
            candidate = value.get("value") or value.get("label")
            if candidate is None:
                try:
                    candidate = next(iter(value.values()))
                except Exception:
                    candidate = None
            return candidate
        return value

    @validator("tipo", pre=True)
    def _tipo_normaliza(cls, value: Any):
        value = cls._extract_value(value)
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @validator("prioridad", pre=True)
    def _prioridad_normaliza(cls, value: Any):
        value = cls._extract_value(value)
        if isinstance(value, str):
            value = value.strip().lower()
        return value or "media"

    @validator("dominio", "nicho", pre=True)
    def _string_desde_dict(cls, value: Any):
        value = cls._extract_value(value)
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


def _fecha_to_str(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


@app.post("/tareas", status_code=201)
def crear_tarea(
    payload: TareaCreate,
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
        logger.debug("[tarea] payload_normalizado=%s", payload.dict())
    except Exception as exc:
        logger.debug("[tarea] no se pudo serializar payload: %s", exc)

    if payload.tipo == "lead" and not payload.dominio:
        raise HTTPException(400, detail="Falta 'dominio' para una tarea de tipo 'lead'")
    if payload.tipo == "nicho" and not payload.nicho:
        raise HTTPException(400, detail="Falta 'nicho' para una tarea de tipo 'nicho'")

    prioridad_value = payload.prioridad or "media"
    if isinstance(prioridad_value, str):
        prioridad_value = prioridad_value.strip().lower() or "media"

    fecha_value = payload.fecha or date.today()
    if isinstance(fecha_value, datetime):
        fecha_value = fecha_value.date()

    timestamp_value = datetime.now(timezone.utc)
    user_email_lower = getattr(usuario, "email_lower", None) or (usuario.email or "").lower()

    logger.debug(
        "INSERT LeadTarea email=%s lower=%s tipo=%s dom=%s nicho=%s fecha=%s prioridad=%s compl=%s",
        usuario.email,
        user_email_lower,
        payload.tipo,
        payload.dominio,
        payload.nicho,
        fecha_value,
        prioridad_value,
        payload.completado,
    )

    tarea = LeadTarea(
        email=usuario.email,
        user_email_lower=user_email_lower,
        texto=payload.texto,
        tipo=payload.tipo,
        dominio=payload.dominio,
        nicho=payload.nicho,
        fecha=fecha_value,
        prioridad=prioridad_value,
        completado=payload.completado,
        timestamp=timestamp_value,
    )

    logger.debug("DEBUG pre-insert timestamp=%r", getattr(tarea, "timestamp", None))

    try:
        db.add(tarea)
        db.commit()
        db.refresh(tarea)
    except IntegrityError as e:
        db.rollback()
        msg = str(getattr(e, "orig", e))
        logger.exception("[tarea] IntegrityError (insert) -> %s", msg)
        raise HTTPException(status_code=400, detail="No se pudo crear la tarea.")
    except Exception as exc:
        db.rollback()
        logger.exception("[tarea] Exception (insert) -> %s", exc)
        raise HTTPException(status_code=400, detail="No se pudo crear la tarea.")

    try:
        UsageService(db).increment(usuario.id, "tasks", 1)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(
            "[usage] IntegrityError incrementando 'tasks' (tarea ya creada). %s",
            getattr(e, "orig", e),
        )
    except Exception as exc:
        db.rollback()
        logger.warning(
            "[usage] Error incrementando 'tasks' (tarea ya creada). %s: %s",
            exc.__class__.__name__,
            exc,
        )

    logger.info(
        "task_created user=%s tipo=%s dominio=%s nicho=%s tarea_id=%s",
        user_email_lower,
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
        "fecha": _fecha_to_str(tarea.fecha),
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
                "fecha": _fecha_to_str(t.fecha),
                "prioridad": t.prioridad,
                "completado": t.completado,
            }
            for t in tareas
        ]
    }


@app.post("/tarea_lead", status_code=201)
def crear_tarea_lead(
    payload: TareaCreate,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        logger.debug(f"[tarea_lead] user={getattr(usuario, 'email', None)} raw_payload={payload.dict()}")
    except Exception:
        pass
    payload_lead = payload.copy(update={"tipo": "lead"})
    return crear_tarea(payload_lead, usuario, db)


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

# --- PROBE DE BASE DE DATOS (para verificar que la app ve la DB correcta) ---
from backend.database import engine, SessionLocal, DATABASE_URL  # <-- tu módulo real

import logging
from sqlalchemy import text
from sqlalchemy.engine import make_url

logger = logging.getLogger("uvicorn")

@app.on_event("startup")
def _db_probe():
    # 1) Muestra la URL enmascarada que REALMENTE usa la app
    url_obj = make_url(DATABASE_URL)
    masked = f"{url_obj.drivername}://***:***@{url_obj.host}:{url_obj.port}/{url_obj.database}"
    if url_obj.query:
        masked += "?" + "&".join(f"{k}={v}" for k, v in url_obj.query.items())
    logger.info(f"DATABASE_URL (masked): {masked}")

    # 2) Interroga la conexión activa
    with engine.connect() as conn:
        info = conn.execute(text("""
            SELECT current_database() AS db,
                   current_user       AS usr,
                   current_schema()   AS schema
        """)).mappings().first()
        logger.info(f"DB probe -> db={info['db']} usr={info['usr']} schema={info['schema']}")

        cols = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name   = 'usuarios'
            ORDER BY 1
        """)).scalars().all()
        logger.info(f"usuarios columns seen by app: {cols}")
# --- FIN PROBE ---