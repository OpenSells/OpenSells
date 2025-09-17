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
from typing import Any, Literal, Optional, List
from backend.models import LeadTarea

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
from dotenv import load_dotenv
load_dotenv()

import logging

# Asegura nivel de logs visible en consola (útil con Uvicorn en Windows)
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
usage_log = logging.getLogger("usage")

# Marcadores visibles para verificar que este archivo es el que corre
print(f"CODE_MARKER /tareas timestamp-fix {__file__}")
logger.info("CODE_MARKER tasks/stability %s", __file__)

# (Opcional pero útil) Ver el SQL real que emite SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.orm.mapper").setLevel(logging.INFO)

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


# --- Compatibilidad con 1_Busqueda.py: endpoints de búsqueda/variantes/extracción ---

class BuscarPayload(BaseModel):
    cliente_ideal: str
    contexto_extra: Optional[str] = None
    forzar_variantes: Optional[bool] = False


@app.post("/buscar")
def generar_variantes(payload: BuscarPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Devuelve una pregunta de refinamiento si el prompt es ambiguo (y no se forzó),
    o bien una lista de 'variantes_generadas' para que el usuario seleccione.
    No consume créditos todavía; eso se hará al extraer/guardar.
    """
    txt = (payload.cliente_ideal or "").strip()
    if not txt:
        raise HTTPException(400, detail="cliente_ideal vacío")

    # Heurística simple de ambigüedad
    es_vago = len(txt) < 8 or txt.split()[-1].lower() in {"servicios", "negocios", "empresas", "tiendas"}
    if es_vago and not payload.forzar_variantes:
        return {"pregunta_sugerida": "¿En qué ciudad o zona te interesan más estos clientes? (Ej.: Madrid Centro)"}

    def _split_categoria_geo(texto: str, contexto_extra: Optional[str]) -> tuple[str, str]:
        t = (texto or "").strip()
        cat, geo = t, ""
        low = t.lower()
        if " en " in low:
            # divide por la última ocurrencia de " en " para evitar cortar frases previas
            idx = low.rfind(" en ")
            cat = t[:idx].strip()
            geo = t[idx + 4 :].strip()
        if not geo and contexto_extra:
            geo = contexto_extra.strip()
        return (cat, geo)

    def _synonyms_for(cat: str) -> list[str]:
        base = cat.lower().strip()
        synmap = {
            "clínica veterinaria": [
                "clínica veterinaria",
                "veterinario",
                "hospital veterinario",
            ],
        }
        synmap.update(
            {
                "dentista": [
                    "dentista",
                    "clínica dental",
                    "odontólogo",
                    "consulta dental",
                ],
                "abogado": [
                    "abogado",
                    "bufete de abogados",
                    "despacho de abogados",
                ],
                "restaurante": [
                    "restaurante",
                    "bar restaurante",
                    "cocina",
                    "comida",
                ],
                "fisioterapeuta": [
                    "fisioterapeuta",
                    "fisioterapia",
                    "clínica de fisioterapia",
                ],
            }
        )
        # match por inclusión para casos "clínica veterinaria de urgencias"
        for k, v in synmap.items():
            if k in base:
                return v
        # fallback: usa la categoría original
        return [cat]

    def build_variants(cliente_ideal: str, contexto_extra: Optional[str]) -> list[str]:
        cat, geo = _split_categoria_geo(cliente_ideal, contexto_extra)
        syns = _synonyms_for(cat)
        intents = ["", "24h", "urgencias", "gatos", "exóticos"]

        candidates = []

        def join_query(parts):
            # une partes no vacías y normaliza espacios
            q = " ".join([p for p in parts if p and p.strip()])
            return " ".join(q.split())

        for s in syns:
            # variante base (sin intención)
            if geo:
                candidates.append(join_query([s, geo]))
            else:
                candidates.append(join_query([s]))

            # variantes con intención
            for it in intents:
                if not it:
                    continue
                if geo:
                    candidates.append(join_query([s, geo, it]))
                else:
                    candidates.append(join_query([s, it]))

        # una variante con exclusiones para reducir ruido de directorios
        exclusions = "-doctoralia -páginasamarillas -facebook -instagram -linkedin"
        if geo:
            candidates.append(join_query([syns[0], geo, exclusions]))
        else:
            candidates.append(join_query([syns[0], exclusions]))

        # dedupe preservando orden
        seen = set()
        variants = []
        for q in candidates:
            qn = q.strip()
            if not qn or qn in seen:
                continue
            seen.add(qn)
            variants.append(qn)

        # limita tamaño (preferible entre 6 y 10), rellena si quedó corto
        if len(variants) < 6:
            base = join_query([cat, geo]) if geo else cat
            extra = [base, f"{base} 24h", f"{base} urgencias", f"{base} exóticos"]
            for q in extra:
                if q not in seen:
                    variants.append(q)
                    seen.add(q)
                if len(variants) >= 6:
                    break

        return variants[:10]

    variantes = build_variants(txt, payload.contexto_extra)
    return {"variantes_generadas": variantes}


class VariantesPayload(BaseModel):
    variantes: List[str]


@app.post("/buscar_variantes_seleccionadas")
def buscar_dominios(payload: VariantesPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Genera 'dominios' a partir de las variantes seleccionadas (placeholder).
    En producción, sustituir por búsqueda real (Google/Maps + scraping).
    """
    if not payload.variantes:
        raise HTTPException(400, detail="variantes vacío")

    dominios = []
    for v in payload.variantes[:3]:
        slug = "".join(ch for ch in v.lower() if ch.isalnum() or ch in "- ").replace(" ", "-")
        if slug:
            dominios.append(f"{slug}.com")
    if not dominios:
        dominios = ["ejemplo-empresa.com", "otra-empresa.com"]

    return {"dominios": list(dict.fromkeys(dominios))[:15]}


class ExtraerMultiplesPayload(BaseModel):
    urls: List[str]
    pais: Optional[str] = "ES"


@app.post("/extraer_multiples")
def extraer_multiples(payload: ExtraerMultiplesPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Simula la extracción de leads de múltiples URLs y devuelve la estructura
    esperada por la UI: { payload_export, resultados }.
    Integra aquí scraping real más adelante (BeautifulSoup + ScraperAPI).
    """
    if not payload.urls:
        raise HTTPException(400, detail="urls vacío")

    # Normaliza dominios
    def _dom(url: str):
        from urllib.parse import urlparse

        u = url if url.startswith("http") else f"https://{url}"
        return urlparse(u).netloc.replace("www.", "")

    resultados = []
    nuevos = 0
    for u in payload.urls[:50]:
        d = _dom(u)
        if not d:
            continue
        # Datos básicos ficticios (placeholder)
        resultados.append({
            "dominio": d,
            "url": f"https://{d}",
            "email": f"info@{d}",
            "telefono": None,
            "origen": "scraping_web",
        })
        nuevos += 1

    # Consumo de cuotas/créditos sin romper planes actuales
    try:
        svc = PlanService(db)
        plan_name, plan = svc.get_effective_plan(usuario)
        ok, remaining, cap = can_start_search(db, usuario.id, plan_name)
        if ok:
            # Capar volumen en free si aplica
            if plan_name == "free" and cap is not None and nuevos > cap:
                resultados = resultados[:cap]
            if plan_name == "free":
                consume_free_search(db, usuario.id, plan_name)
            else:
                # Créditos en función de leads únicos
                consume_lead_credits(db, usuario.id, plan_name, len(resultados))
            db.commit()
    except Exception as e:
        logger.warning("[extraer_multiples] no se pudo registrar uso: %s", e)

    payload_export = {
        "filename": f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        # La UI añade 'nicho' antes de llamar a /exportar_csv
    }

    return {"payload_export": payload_export, "resultados": resultados}


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


class TareaEditPayload(BaseModel):
    texto: Optional[str] = None
    fecha: Optional[date] = None
    prioridad: Optional[Literal["alta", "media", "baja"]] = None
    tipo: Optional[Literal["general", "nicho", "lead"]] = None
    nicho: Optional[str] = None
    dominio: Optional[str] = None
    auto: Optional[bool] = None
    completado: Optional[bool] = None


def _fecha_to_str(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _tarea_to_dict(t):
    return {
        "id": t.id,
        "texto": t.texto,
        "tipo": t.tipo,
        "nicho": t.nicho,
        "dominio": t.dominio,
        "fecha": _fecha_to_str(t.fecha),
        "prioridad": t.prioridad,
        "completado": t.completado,
        "timestamp": getattr(t, "timestamp", None).isoformat() if getattr(t, "timestamp", None) else None,
    }


from datetime import date, datetime
from sqlalchemy import func, insert
from sqlalchemy.exc import IntegrityError
from backend.models import LeadTarea

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

    user_email_lower = getattr(usuario, "email_lower", None) or (usuario.email or "").lower()

    # Usamos la tabla real para referenciar columnas reales (evita desalineaciones)
    tbl = LeadTarea.__table__

    # Insert con timestamp puesto por la BD (func.now()) — imposible que vaya NULL
    stmt = (
        insert(tbl)
        .values({
            tbl.c.email:            usuario.email,
            tbl.c.user_email_lower: user_email_lower,
            tbl.c.texto:            payload.texto,
            tbl.c.tipo:             payload.tipo,
            tbl.c.dominio:          payload.dominio,
            tbl.c.nicho:            payload.nicho,
            tbl.c.fecha:            fecha_value,         # date
            tbl.c.prioridad:        prioridad_value,
            tbl.c.completado:       payload.completado,
            tbl.c.timestamp:        func.now(),          # 👈 lo fija Postgres en el INSERT
        })
        .returning(tbl.c.id)
    )

    try:
        new_id = db.execute(stmt).scalar_one()
        db.commit()
        tarea = db.get(LeadTarea, new_id)
    except IntegrityError as e:
        db.rollback()
        msg = str(getattr(e, "orig", e))
        logger.exception("[tarea] IntegrityError (insert) -> %s", msg)
        raise HTTPException(status_code=400, detail=f"DB IntegrityError: {msg}")
    except Exception as exc:
        db.rollback()
        logger.exception("[tarea] Exception (insert) -> %s", exc)
        raise HTTPException(status_code=400, detail=f"Error creando tarea: {exc.__class__.__name__}: {exc}")

    # Incremento de uso: si falla, no rompe la tarea
    try:
        UsageService(db).increment(usuario.id, "tasks", 1)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning("[usage] IntegrityError incrementando 'tasks' (tarea ya creada). %s", getattr(e, "orig", e))
    except Exception as exc:
        db.rollback()
        logger.warning("[usage] Error incrementando 'tasks' (tarea ya creada). %s: %s", exc.__class__.__name__, exc)

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


from typing import Optional, Literal
from fastapi import HTTPException  # ← quitamos Query
from datetime import timezone
# Asegúrate de tener importados: Depends, Session y LeadTarea en este archivo.

@app.get("/tareas")
def listar_tareas(
    tipo: Optional[Literal["general", "nicho", "lead"]] = None,
    nicho: Optional[str] = None,
    dominio: Optional[str] = None,
    solo_pendientes: bool = False,
    limit: int = 100,
    offset: int = 0,
    usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # normaliza email
    user_lower = getattr(usuario, "email_lower", None) or (usuario.email or "").lower()

    # sanea parámetros (evita valores raros al invocar internamente)
    if tipo not in ("general", "nicho", "lead"):
        tipo = None
    if not (isinstance(nicho, str) and nicho.strip()):
        nicho = None
    if not (isinstance(dominio, str) and dominio.strip()):
        dominio = None

    # clamp simple para evitar valores extremos al no usar Query(ge/le)
    limit = max(1, min(500, int(limit)))
    offset = max(0, int(offset))

    q = db.query(LeadTarea).filter(LeadTarea.user_email_lower == user_lower)

    if tipo:
        q = q.filter(LeadTarea.tipo == tipo)
    if nicho:
        q = q.filter(LeadTarea.nicho == nicho)
    if dominio:
        q = q.filter(LeadTarea.dominio == dominio)
    if solo_pendientes:
        q = q.filter(LeadTarea.completado.is_(False))

    total = q.count()

    tareas = (
        q.order_by(LeadTarea.timestamp.desc(), LeadTarea.id.desc())
         .offset(offset)
         .limit(limit)
         .all()
    )

    def iso_or_none(dt):
        if not dt:
            return None
        try:
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            return dt.isoformat()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
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
                "timestamp": iso_or_none(getattr(t, "timestamp", None)),
            }
            for t in tareas
        ],
    }


@app.post("/tarea_completada")
def marcar_tarea_completada(
    tarea_id: int,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_lower = getattr(usuario, "email_lower", None) or (usuario.email or "").lower()
    t = (
        db.query(LeadTarea)
        .filter(LeadTarea.id == tarea_id, LeadTarea.user_email_lower == user_lower)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    if not t.completado:
        t.completado = True
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"No se pudo completar la tarea: {exc}")

    return {"ok": True, "tarea": _tarea_to_dict(t)}


@app.post("/editar_tarea")
def editar_tarea(
    tarea_id: int,
    payload: TareaEditPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_lower = getattr(usuario, "email_lower", None) or (usuario.email or "").lower()
    t = (
        db.query(LeadTarea)
        .filter(LeadTarea.id == tarea_id, LeadTarea.user_email_lower == user_lower)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    if payload.texto is not None:
        t.texto = payload.texto.strip()
    if payload.fecha is not None:
        t.fecha = payload.fecha
    if payload.prioridad is not None:
        t.prioridad = payload.prioridad.strip().lower()
    if payload.tipo is not None:
        t.tipo = payload.tipo.strip().lower()
    if payload.nicho is not None:
        t.nicho = payload.nicho.strip()
    if payload.dominio is not None:
        t.dominio = payload.dominio.strip()
    if payload.auto is not None:
        t.auto = bool(payload.auto)
    if payload.completado is not None:
        t.completado = bool(payload.completado)

    try:
        db.commit()
        db.refresh(t)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se pudo editar la tarea: {exc}")

    return {"ok": True, "tarea": _tarea_to_dict(t)}


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


from typing import Optional

@app.get("/tareas_pendientes")
def tareas_pendientes(
    tipo: Optional[str] = None,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Normaliza por si llega vacío o con espacios
    if not (isinstance(tipo, str) and tipo.strip()):
        tipo = None

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