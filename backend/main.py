# --- Standard library ---
import asyncio
import csv
import io
import os
import logging
import re
from urllib.parse import urlparse

# --- Third-party ---
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator, root_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func, select, text
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional, List
from backend.models import LeadTarea

import httpx

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



def normalizar_dominio(value: str) -> str:
    if not value:
        return ""
    v = value.strip()
    if v.startswith("http://") or v.startswith("https://"):
        try:
            netloc = urlparse(v).netloc
            v = netloc or v
        except Exception:
            pass
    v = re.sub(r"^www\.", "", v, flags=re.IGNORECASE)
    v = v.lower()
    v = v.split("/")[0].strip()
    return v


# --- Búsqueda y scraping ---

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
MAX_SEARCH_RESULTS = 60
MAX_LEADS_PER_EXTRACTION = 30
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}")
CONTACT_PATHS: tuple[str, ...] = (
    "/contacto",
    "/contact",
    "/aviso-legal",
    "/legal",
    "/politica-privacidad",
)
BLOCKED_PATTERNS = (
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "linkedin.com",
    "doctoralia.es",
    "paginasamarillas.es",
    "tripadvisor.es",
    "habitissimo.es",
    "youtube.com",
    "yelp.com",
    "maps.google.",
)
KNOWN_MULTI_TLDS = {
    "com.ar",
    "com.br",
    "com.co",
    "com.ec",
    "com.es",
    "com.mx",
    "com.pe",
    "com.cl",
    "com.ve",
    "co.uk",
}


def base_domain(domain: str) -> str:
    if not domain:
        return ""
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    last_two = ".".join(parts[-2:])
    last_three = ".".join(parts[-3:])
    if last_two in KNOWN_MULTI_TLDS and len(parts) >= 3:
        return last_three
    return last_two


def _is_blocked_domain(domain: str) -> bool:
    domain = domain.lower()
    for pattern in BLOCKED_PATTERNS:
        pat = pattern.lower()
        if pat.endswith("."):
            if domain.startswith(pat):
                return True
        if domain == pat:
            return True
        if domain.endswith(f".{pat}"):
            return True
    return False


def search_domains(queries: list[str], per_query: int = 20) -> list[str]:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        logger.error("[buscar_variantes_seleccionadas] falta BRAVE_API_KEY para búsquedas")
        raise HTTPException(
            status_code=503,
            detail="Busqueda no configurada: BRAVE_API_KEY ausente",
        )

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    dominios: list[str] = []
    vistos: set[str] = set()

    with httpx.Client(timeout=10) as client:
        for query in queries:
            q = (query or "").strip()
            if not q:
                continue
            try:
                resp = client.get(
                    BRAVE_SEARCH_URL,
                    params={"q": q, "count": per_query},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("[buscar_variantes_seleccionadas] fallo consulta Brave q=%s err=%s", q, exc)
                continue

            results = data.get("web", {}).get("results", []) or []
            for item in results:
                url = item.get("url") or ""
                normalized = normalizar_dominio(url)
                if not normalized:
                    continue
                if _is_blocked_domain(normalized):
                    continue
                domain = base_domain(normalized)
                if not domain or _is_blocked_domain(domain):
                    continue
                if domain in vistos:
                    continue
                vistos.add(domain)
                dominios.append(domain)
                if len(dominios) >= MAX_SEARCH_RESULTS:
                    break
            logger.info(
                "[buscar_variantes_seleccionadas] query=%s dominios_parciales=%d",
                q,
                len(vistos),
            )
            if len(dominios) >= MAX_SEARCH_RESULTS:
                break

    logger.info(
        "[buscar_variantes_seleccionadas] dominios_unicos_totales=%d",
        len(vistos),
    )
    return dominios


async def _fetch_email_for_domain(client: httpx.AsyncClient, domain: str) -> Optional[str]:
    async def get_text(url: str) -> str:
        try:
            resp = await client.get(url, timeout=8)
            if resp.status_code < 400:
                return resp.text or ""
        except Exception as exc:
            logger.debug("[scrape] fallo request url=%s err=%s", url, exc)
        return ""

    base_url = f"https://{domain}"
    html = await get_text(base_url)
    matches = EMAIL_RE.findall(html)
    if matches:
        return matches[0]

    for idx, path in enumerate(CONTACT_PATHS, start=1):
        if idx > 2:
            break
        html = await get_text(f"{base_url}{path}")
        matches = EMAIL_RE.findall(html)
        if matches:
            return matches[0]
    return None


async def scrape_domains(domains: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_fetch_email_for_domain(client, d) for d in domains]
        emails = await asyncio.gather(*tasks, return_exceptions=True)

    for domain, email in zip(domains, emails):
        if isinstance(email, Exception):
            logger.debug("[scrape] excepción dominio=%s err=%s", domain, email)
            email_value = None
        else:
            email_value = email
        results.append(
            {
                "dominio": domain,
                "url": f"https://{domain}",
                "email": email_value,
                "telefono": None,
                "origen": "scraping_web",
            }
        )

    return results


# --- Compatibilidad con 1_Busqueda.py: endpoints de búsqueda/variantes/extracción ---

EXTENDED_PREFIX = "[Búsqueda extendida] "


def build_variantes_display(variantes: list[str]) -> tuple[list[str], bool, Optional[int]]:
    out = list(variantes)
    has_extended = False
    extended_idx: Optional[int] = None
    if len(out) >= 5:
        extended_idx = len(out) - 1
        out[extended_idx] = f"{EXTENDED_PREFIX}{out[extended_idx]}"
        has_extended = True
    return out, has_extended, extended_idx


def normalize_client_variantes(payload_variantes: Optional[list[str]]) -> list[str]:
    result: list[str] = []
    if not payload_variantes:
        return result
    for variante in payload_variantes:
        v = (variante or "").strip()
        if v.startswith(EXTENDED_PREFIX):
            v = v[len(EXTENDED_PREFIX) :]
        result.append(v.strip())
    return result

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

    # 4. Generar variantes (exactamente 5, limpias y útiles para scraping)
    def _norm(s: str) -> str:
        return " ".join((s or "").strip().split())

    def _split_cat_geo(texto: str, contexto_extra: Optional[str]) -> tuple[str, str]:
        t = _norm(texto)
        low = t.lower()
        cat, geo = t, ""
        if " en " in low:
            idx = low.rfind(" en ")
            cat = _norm(t[:idx])
            geo = _norm(t[idx + 4 :])
        if not geo and contexto_extra:
            geo = _norm(contexto_extra)
        return (cat, geo)

    def _fallback_variants(texto: str, contexto_extra: Optional[str]) -> list[str]:
        cat, geo = _split_cat_geo(texto, contexto_extra)
        base_geo = f"{geo}" if geo else ""
        cat_low = cat.lower()
        synmap = {
            "clínica veterinaria": ["clínica veterinaria", "veterinario", "hospital veterinario"],
            "veterinario": ["veterinario", "clínica veterinaria", "hospital veterinario"],
            "dentista": ["dentista", "clínica dental", "odontólogo"],
            "abogado": ["abogado", "bufete de abogados", "despacho de abogados"],
            "fisioterapeuta": ["fisioterapeuta", "clínica de fisioterapia"],
            "restaurante": ["restaurante", "bar restaurante"],
            "inmobiliaria": ["inmobiliaria", "agencia inmobiliaria"],
        }
        syns = None
        for k, v in synmap.items():
            if k in cat_low:
                syns = v
                break
        if not syns:
            syns = [cat]

        intents: list[str] = []
        if "veterin" in cat_low:
            intents = ["24h", "urgencias"]
        elif "dent" in cat_low:
            intents = ["implantes", "urgencias"]
        elif "abog" in cat_low:
            intents = ["laboral", "penal"]
        elif "fisioterap" in cat_low:
            intents = ["deportiva", "suelo pélvico"]

        excl = (
            "-site:facebook.com -site:instagram.com -site:twitter.com -site:linkedin.com "
            "-site:doctoralia.es -site:paginasamarillas.es -site:tripadvisor.es -site:habitissimo.es"
        )

        def q(*parts):
            s = _norm(" ".join(p for p in parts if p))
            return s.rstrip(".")

        candidates = []
        candidates.append(q(syns[0], base_geo))
        candidates.append(q(syns[1] if len(syns) > 1 else syns[0], base_geo))
        if intents:
            candidates.append(q(syns[0], base_geo, intents[0]))
            if len(intents) > 1:
                candidates.append(q(syns[0], base_geo, intents[1]))
        else:
            candidates.append(q(syns[0], base_geo, "servicio"))
            candidates.append(q(syns[0], base_geo, "profesional"))
        candidates.append(q(syns[0], base_geo, excl))

        final: list[str] = []
        seen: set[str] = set()
        for c in candidates:
            key = c.lower()
            if c and key not in seen:
                final.append(c)
                seen.add(key)
            if len(final) == 5:
                break
        while len(final) < 5:
            extra = q(syns[0], base_geo)
            if extra.lower() not in seen:
                final.append(extra)
                seen.add(extra.lower())
        return final[:5]

    def _clean_lines(text: str) -> list[str]:
        raw = [ln.strip() for ln in text.split("\n") if ln.strip()]
        lines: list[str] = []
        for ln in raw:
            ln = ln.lstrip("-•*1234567890. ").strip()
            ln = ln.replace(" + ", " ").replace("+", " ")
            ln = ln.strip().strip('"').strip("'")
            ln = _norm(ln).rstrip(".")
            if ln:
                lines.append(ln)
        seen: set[str] = set()
        cleaned: list[str] = []
        for ln in lines:
            kl = ln.lower()
            if kl not in seen:
                cleaned.append(ln)
                seen.add(kl)
        return cleaned

    contexto_extra = payload.contexto_extra or ""
    cliente_ideal = txt

    openai_client = None
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI

            openai_client = OpenAI(api_key=api_key)
        except Exception as exc:
            logger.warning("No se pudo inicializar OpenAI: %s", exc)
            openai_client = None

    if openai_client:
        prompt_variantes = f"""
Eres un generador de consultas para Google/Maps orientadas a scraping de leads.

Entrada (intención del usuario y cliente ideal):
"{cliente_ideal}"
Contexto extra (opcional): "{contexto_extra}"

Genera EXACTAMENTE 5 consultas de búsqueda diferentes y útiles (una por línea) que:
- Representen fielmente la intención y el cliente ideal.
- Sean óptimas para encontrar webs de negocio reales (no directorios).
- Usen sinónimos/nombres equivalentes del sector cuando ayude.
- Incluyan la localización si se deduce de la entrada.
- Pueden incluir UNA sola variante con exclusiones para filtrar directorios/redes, usando -site:dominio (p.ej. -site:facebook.com -site:instagram.com ...).
- NO usen “+”, NO terminen en punto, NO devuelvas viñetas ni numeración.
- Máximo ~10 palabras por consulta.

SALIDA: 5 líneas, cada línea es una consulta. Sin texto extra.
"""
        try:
            respuesta = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_variantes}],
                temperature=0.4,
            )
            contenido = respuesta.choices[0].message.content
            variantes = _clean_lines(contenido)
            variantes = [v for v in variantes if v]
            variantes = [v for v in variantes if len(v.split()) >= 2]
            if len(variantes) > 5:
                variantes = variantes[:5]
            if len(variantes) < 5:
                faltan = 5 - len(variantes)
                variantes += _fallback_variants(cliente_ideal, contexto_extra)[:faltan]
        except Exception as e:
            logger.warning("Fallo OpenAI en /buscar, usando fallback: %s", e)
            variantes = _fallback_variants(cliente_ideal, contexto_extra)
    else:
        variantes = _fallback_variants(cliente_ideal, contexto_extra)

    variantes_display, has_extended_variant, extended_index = build_variantes_display(variantes)

    return {
        "variantes_generadas": variantes,
        "variantes": variantes,
        "has_extended_variant": has_extended_variant,
        "extended_index": extended_index,
        "variantes_display": variantes_display,
    }


class VariantesPayload(BaseModel):
    variantes: List[str]
    variantes_display: Optional[List[str]] = None

    @root_validator(pre=True)
    def _merge_variantes(cls, values):
        if not values.get("variantes") and values.get("variantes_display"):
            values["variantes"] = values.get("variantes_display")
        return values

    @validator("variantes", pre=True)
    def _normalize_variantes(cls, value):
        return normalize_client_variantes(value)


@app.post("/buscar_variantes_seleccionadas")
def buscar_dominios(payload: VariantesPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Genera 'dominios' a partir de las variantes seleccionadas realizando
    consultas reales contra Brave Search.
    """
    if not payload.variantes:
        raise HTTPException(400, detail="variantes vacío")

    queries = [v for v in payload.variantes if v]
    dominios = search_domains(queries)
    logger.info(
        "[buscar_variantes_seleccionadas] user=%s queries=%d dominios=%d",
        getattr(usuario, "email_lower", None),
        len(queries),
        len(dominios),
    )

    if not dominios:
        raise HTTPException(502, detail="No se encontraron dominios para las variantes proporcionadas")

    return {"dominios": dominios[:MAX_SEARCH_RESULTS]}


class ExtraerMultiplesPayload(BaseModel):
    urls: List[str]
    pais: Optional[str] = "ES"


class LeadPayloadItem(BaseModel):
    dominio: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    origen: Optional[str] = None


class GuardarLeadsPayload(BaseModel):
    nicho: str
    nicho_original: Optional[str] = None
    items: List[LeadPayloadItem]


class NichoSummary(BaseModel):
    nicho: str
    nicho_original: str
    leads: int


class LeadItem(BaseModel):
    id: int | None = None
    dominio: str
    url: str
    estado_contacto: str | None = None
    timestamp: datetime
    nicho: str
    nicho_original: str


@app.post("/extraer_multiples")
def extraer_multiples(payload: ExtraerMultiplesPayload, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Extrae leads desde los dominios recibidos realizando un scraping ligero y
    devuelve la estructura esperada por la UI: { payload_export, resultados }.
    """
    if not payload.urls:
        raise HTTPException(400, detail="urls vacío")

    raw_domains = []
    seen: set[str] = set()
    for url in payload.urls:
        dom = normalizar_dominio(url)
        if not dom:
            continue
        if dom in seen:
            continue
        seen.add(dom)
        raw_domains.append(dom)

    domains_slice = raw_domains[:MAX_LEADS_PER_EXTRACTION]
    if not domains_slice:
        raise HTTPException(400, detail="No se encontraron dominios válidos para extraer")

    try:
        resultados = asyncio.run(scrape_domains(domains_slice))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            resultados = loop.run_until_complete(scrape_domains(domains_slice))
        finally:
            loop.close()

    nuevos = len(resultados)
    logger.info(
        "[extraer_multiples] user=%s dominios_solicitados=%d dominios_utilizados=%d",
        getattr(usuario, "email_lower", None),
        len(payload.urls),
        nuevos,
    )

    # Consumo de cuotas/créditos sin romper planes actuales
    try:
        svc = PlanService(db)
        plan_name, plan = svc.get_effective_plan(usuario)
        ok, remaining, cap = can_start_search(db, usuario.id, plan_name)
        if ok:
            # Capar volumen en free si aplica
            if plan_name == "free" and cap is not None and nuevos > cap:
                resultados = resultados[:cap]
                nuevos = len(resultados)
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


@app.post("/guardar_leads")
def guardar_leads(
    payload: GuardarLeadsPayload,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.nicho:
        raise HTTPException(status_code=400, detail="Falta 'nicho'")
    nicho_norm = payload.nicho.strip()
    logger.info(
        "[guardar_leads] user=%s nicho=%s nicho_normalizado=%s total_items=%s",
        getattr(usuario, "email_lower", None),
        getattr(payload, "nicho", None),
        nicho_norm,
        len(payload.items) if getattr(payload, "items", None) else 0,
    )
    if not payload.items:
        return {
            "insertados": 0,
            "saltados": 0,
            "total_recibidos": 0,
            "nicho": nicho_norm,
        }

    tbl = LeadExtraido.__table__
    to_insert = []
    total_recibidos = len(payload.items)
    nicho_orig = (payload.nicho_original or payload.nicho).strip() or nicho_norm
    filtered_out = 0

    for r in payload.items:
        dom = normalizar_dominio(r.dominio or r.url or "")
        if not dom:
            filtered_out += 1
            continue
        url_val = r.url or (f"https://{dom}")
        if url_val and not url_val.startswith("http"):
            url_val = f"https://{url_val}"

        to_insert.append(
            {
                "user_email": usuario.email,
                "user_email_lower": usuario.email_lower,
                "dominio": dom,
                "url": url_val,
                "timestamp": func.now(),
                "nicho": nicho_norm,
                "nicho_original": nicho_orig,
                "estado_contacto": "nuevo",
            }
        )

    if not to_insert:
        logger.info(
            "[guardar_leads] user=%s sin filas válidas (filtrados=%s)",
            getattr(usuario, "email_lower", None),
            filtered_out,
        )
        return {
            "insertados": 0,
            "saltados": 0,
            "total_recibidos": total_recibidos,
            "nicho": nicho_norm,
        }

    stmt = (
        pg_insert(tbl)
        .values(to_insert)
        .on_conflict_do_nothing(index_elements=[tbl.c.user_email_lower, tbl.c.dominio])
        .returning(tbl.c.dominio)
    )

    try:
        result = db.execute(stmt)
        inserted_domains = [row[0] for row in result.fetchall()]
        insertados = len(inserted_domains)
        db.commit()
        logger.info(
            "[guardar_leads] user=%s nicho=%s insertados=%s duplicados=%s filtrados=%s",
            getattr(usuario, "email_lower", None),
            nicho_norm,
            insertados,
            max(len(to_insert) - insertados, 0),
            filtered_out,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("[guardar_leads] error al insertar leads")
        raise HTTPException(status_code=500, detail=str(exc))

    saltados = max(len(to_insert) - insertados, 0)
    return {
        "insertados": insertados,
        "saltados": saltados,
        "total_recibidos": total_recibidos,
        "nicho": nicho_norm,
    }


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


@app.get("/mis_nichos", response_model=list[NichoSummary])
def mis_nichos(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    u = user.email.lower()
    query = (
        select(
            LeadExtraido.nicho.label("nicho"),
            func.min(LeadExtraido.nicho_original).label("nicho_original"),
            func.count().label("leads"),
        )
        .where(LeadExtraido.user_email_lower == u)
        .group_by(LeadExtraido.nicho)
        .order_by(LeadExtraido.nicho)
    )
    try:
        rows = db.execute(query).all()
    except Exception as exc:
        logger.exception("[mis_nichos] error al consultar nichos")
        raise HTTPException(status_code=500, detail=str(exc))

    data = [
        NichoSummary(
            nicho=row.nicho,
            nicho_original=(row.nicho_original or row.nicho),
            leads=int(row.leads),
        )
        for row in rows
        if row.nicho
    ]
    logger.info("[mis_nichos] user=%s nichos=%d", u, len(data))
    return data



@app.get("/leads_por_nicho")
def leads_por_nicho(
    nicho: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    nicho = (nicho or "").strip()
    if not nicho:
        raise HTTPException(status_code=400, detail="Falta 'nicho'")

    u = user.email.lower()
    query = (
        select(
            LeadExtraido.id,
            LeadExtraido.dominio,
            LeadExtraido.url,
            LeadExtraido.estado_contacto,
            LeadExtraido.timestamp,
            LeadExtraido.nicho,
            LeadExtraido.nicho_original,
        )
        .where(
            LeadExtraido.user_email_lower == u,
            LeadExtraido.nicho == nicho,
        )
        .order_by(LeadExtraido.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )

    try:
        result = db.execute(query)
    except Exception as exc:
        logger.exception("[leads_por_nicho] error user=%s nicho=%s", u, nicho)
        raise HTTPException(status_code=500, detail=str(exc))

    rows = result.fetchall()
    items = [
        LeadItem(
            id=row.id,
            dominio=row.dominio,
            url=row.url,
            estado_contacto=row.estado_contacto,
            timestamp=row.timestamp,
            nicho=row.nicho,
            nicho_original=(row.nicho_original or row.nicho),
        ).dict()
        for row in rows
    ]

    logger.info("[leads_por_nicho] user=%s nicho=%s count=%d", u, nicho, len(items))
    return {"items": items, "limit": limit, "offset": offset, "count": len(items)}


@app.get("/exportar_leads_nicho")
def exportar_leads_nicho(
    nicho: str = Query(..., description="Nombre del nicho a exportar"),
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nicho = (nicho or "").strip()
    if not nicho:
        raise HTTPException(status_code=400, detail="Falta 'nicho'")

    stmt = (
        select(
            LeadExtraido.dominio,
            LeadExtraido.url,
            LeadExtraido.estado_contacto,
            LeadExtraido.timestamp,
            LeadExtraido.nicho,
            LeadExtraido.nicho_original,
        )
        .where(
            LeadExtraido.user_email_lower == usuario.email_lower,
            LeadExtraido.nicho == nicho,
        )
        .order_by(LeadExtraido.timestamp.desc())
    )

    try:
        rows = db.execute(stmt).all()
    except Exception as exc:
        logger.exception(
            "[exportar_leads_nicho] error obteniendo datos user=%s nicho=%s",
            getattr(usuario, "email_lower", None),
            nicho,
        )
        raise HTTPException(status_code=500, detail=str(exc))

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["dominio", "url", "estado_contacto", "timestamp", "nicho", "nicho_original"])
    for row in rows:
        writer.writerow(
            [
                row.dominio or "",
                row.url or "",
                row.estado_contacto or "",
                row.timestamp.isoformat() if row.timestamp else "",
                row.nicho or "",
                row.nicho_original or "",
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")

    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", nicho.lower()).strip("-") or "nicho"
    filename = f"leads_{safe_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

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

    try:
        registro = HistorialExport(user_email=usuario.email_lower, filename=filename)
        db.add(registro)
        consume_csv_export(db, usuario.id, plan_name)
        db.commit()
        logger.info(
            "[exportar_leads_nicho] user=%s nicho=%s filas=%s filename=%s",
            getattr(usuario, "email_lower", None),
            nicho,
            len(rows),
            filename,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("[exportar_leads_nicho] error al registrar historial")
        raise HTTPException(status_code=500, detail=str(exc))

    response = StreamingResponse(iter([csv_bytes]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response




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
        tbl.insert()
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
    variantes: Optional[List[str]] = None
    variantes_display: Optional[List[str]] = None

    @root_validator(pre=True)
    def _merge_variantes(cls, values):
        if not values.get("variantes") and values.get("variantes_display"):
            values["variantes"] = values.get("variantes_display")
        return values

    @validator("variantes", pre=True)
    def _normalize_variantes(cls, value):
        if value is None:
            return None
        return normalize_client_variantes(value)

    def variantes_normalizadas(self) -> list[str]:
        return self.variantes or []


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

    variantes_cliente = payload.variantes_normalizadas()

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
        pg_insert(LeadEstado)
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