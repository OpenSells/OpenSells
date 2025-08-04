from backend.db import obtener_todas_tareas_pendientes_postgres as obtener_todas_tareas_pendientes
from backend.db import eliminar_lead_completamente
from backend.db import obtener_tarea_por_id_postgres as obtener_tarea_por_id
from fastapi import UploadFile
from backend.db import normalizar_dominio
from backend.db import guardar_info_extra, obtener_info_extra
from backend.db import eliminar_lead_de_nicho
from backend.db import guardar_memoria_usuario, obtener_memoria_usuario
from backend.db import guardar_evento_historial_postgres as guardar_evento_historial, obtener_historial_por_dominio_postgres as obtener_historial_por_dominio
from backend.db import marcar_tarea_completada_postgres as marcar_tarea_completada
# Utilidad para buscar leads guardados en la base de datos PostgreSQL
# Se importa sin alias para usar el mismo nombre en el endpoint y evitar
# confusiones con la versión SQLite (buscar_leads_global) presente en db.py
from backend.db import buscar_leads_global_postgres
from pydantic import BaseModel
from fastapi import FastAPI, Body, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import requests
import logging
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import unicodedata
import re
from fastapi.responses import StreamingResponse
from io import BytesIO
import asyncio
from time import perf_counter
import csv

# Cargar variables de entorno antes de usar Stripe
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# BD & seguridad
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from backend.database import engine, Base, get_db
from backend.models import Usuario
from backend.auth import (
    hashear_password,
    verificar_password,
    crear_token,
    obtener_usuario_por_email,
    get_current_user,
)

from fastapi import Depends

def validar_suscripcion(usuario = Depends(get_current_user)):
    if not usuario.plan or usuario.plan == "free":
        raise HTTPException(
            status_code=403,
            detail="Debes tener una suscripción activa para usar esta función."
        )
    return usuario

# Historial de exportaciones y leads
from backend.db import (
    crear_tablas_si_no_existen,
    guardar_exportacion,
    guardar_leads_extraidos,
    obtener_historial,
    obtener_nichos_usuario,
    obtener_leads_por_nicho,
    eliminar_nicho_postgres,
    obtener_urls_extraidas_por_nicho,
)

from backend.db import guardar_estado_lead, obtener_estado_lead
from sqlalchemy.orm import Session
from backend.db import obtener_nichos_para_url
from backend.webhook import router as webhook_router

load_dotenv()

app = FastAPI()
app.include_router(webhook_router)

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    crear_tablas_si_no_existen()  # ✅ función síncrona, se llama normal

def normalizar_nicho(texto: str) -> str:
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    return texto.strip('_')

from urllib.parse import urlparse

def extraer_dominio_base(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        dominio = urlparse(url).netloc
    else:
        dominio = urlparse("http://" + url).netloc  # ← SOLUCIÓN
    return dominio.replace("www.", "").strip()

openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_key) if openai_key else None
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")

class MemoriaUsuarioRequest(BaseModel):
    descripcion: str

class Busqueda(BaseModel):
    cliente_ideal: str

class VariantesSeleccionadasRequest(BaseModel):
    variantes: list[str]

class UrlsMultiples(BaseModel):
    urls: list[str]
    pais: str = "ES"

class ExportarCSVRequest(BaseModel):
    urls: list[str]
    pais: str = "ES"
    nicho: str

class UsuarioRegistro(BaseModel):
    email: str
    password: str

from sqlalchemy.orm import Session  # asegúrate de tener este import arriba

@app.post("/register")
def register(user: UsuarioRegistro, db: Session = Depends(get_db)):
    db_user = obtener_usuario_por_email(user.email, db)
    if db_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    nuevo_usuario = Usuario(email=user.email, hashed_password=hashear_password(user.password))
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario registrado correctamente"}

from sqlalchemy.orm import Session  # asegúrate de tener este import en la parte superior

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = obtener_usuario_por_email(form_data.username, db)
    if not user or not verificar_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = crear_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/protegido")
async def protegido(usuario = Depends(get_current_user)):
    return {
        "mensaje": f"Bienvenido, {usuario.email}",
        "email": usuario.email,
        "plan": usuario.plan or "free"
    }

@app.get("/")
def inicio():
    return {"mensaje": "¡Bienvenido al Wrapper Automático!"}

class BuscarRequest(BaseModel):
    cliente_ideal: str
    forzar_variantes: Optional[bool] = False
    contexto_extra: Optional[str] = None

@app.post("/buscar")
async def generar_variantes_cliente_ideal(
    request: BuscarRequest,
    usuario=Depends(get_current_user)
):
    if openai_client is None:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurado")
    cliente_ideal = request.cliente_ideal.strip()
    forzar_variantes = request.forzar_variantes or False
    contexto_extra = request.contexto_extra or ""

    # 1. Si no hay contexto manual ni forzar_variantes, intenta cargar memoria automáticamente
    if not forzar_variantes and not contexto_extra:
        memoria = obtener_memoria_usuario(usuario.email)
        if memoria:
            contexto_extra = f"El usuario indicó esto sobre su negocio: {memoria}"

    # 2. Construcción final del prompt
    prompt_base = cliente_ideal
    if contexto_extra:
        prompt_base += f". {contexto_extra}"

    # 3. Evaluación del input inicial si no se fuerza
    if not forzar_variantes:
        evaluacion_prompt = f"""
Un usuario ha escrito la siguiente búsqueda para encontrar leads: "{prompt_base}".

Si la búsqueda no menciona específicamente el sector, el tipo de cliente o el servicio concreto que busca, responde con una pregunta breve para pedir más contexto.

Si está todo claro y específico, responde solo con OK.
"""
        decision = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": evaluacion_prompt}],
            temperature=0.3
        ).choices[0].message.content.strip()

        if decision != "OK":
            return {"pregunta_sugerida": decision}

    # 4. Generar variantes
    prompt_variantes = f"""
Dado el nicho o búsqueda "{prompt_base}", genera exactamente 6 palabras clave o frases similares que puedan servir para encontrar leads en Google. Incluye sinónimos, servicios relacionados, etc. Solo devuelve una lista con viñetas:
- ...
- ...
"""
    respuesta = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt_variantes}],
        temperature=0.7
    )

    contenido = respuesta.choices[0].message.content.strip()
    variantes = [line.strip("- ").strip() for line in contenido.split("\n") if line.strip()]

    return {
        "variantes_generadas": variantes
    }

@app.post("/buscar_variantes_seleccionadas")
def buscar_urls_desde_variantes(payload: VariantesSeleccionadasRequest):
    variantes = payload.variantes[:3]

    if openai_client is None:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurado")

    detectar_pais_prompt = f"""
Dado el siguiente conjunto de variantes de búsqueda:

{chr(10).join(variantes)}

¿En qué país parece estar interesado el usuario?

Devuelve únicamente el código ISO alfa-2 del país (por ejemplo ES, MX, GT). Si no se puede deducir, responde ANY.
"""
    respuesta_pais = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": detectar_pais_prompt}],
        temperature=0.2
    )

    codigo_pais = respuesta_pais.choices[0].message.content.strip().upper()
    if not re.match(r"^[A-Z]{2}$", codigo_pais):
        codigo_pais = "ANY"

    paginas_por_variante = 3
    resultados_por_pagina = 10
    todas_urls = []
    paginas_procesadas = 0

    for variante in variantes:
        query = variante
        logger.info(f"Procesando variante: '{query}'")

        for pagina in range(paginas_por_variante):
            start = pagina * resultados_por_pagina
            logger.info(f"Página {pagina+1} (start={start})")

            params = {
                'api_key': SCRAPERAPI_KEY,
                'query': query,
                'num': str(resultados_por_pagina),
                'start': str(start)
            }
            if codigo_pais != "ANY":
                params['country_code'] = codigo_pais.lower()

            try:
                resultado = requests.get(
                    'https://api.scraperapi.com/structured/google/search',
                    params=params,
                    timeout=60
                ).json()

                links = [res.get('link') for res in resultado.get('organic_results', [])]
                # ❗ Filtro para excluir archivos
                extensiones_no_deseadas = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.xml', '.ppt', '.pptx', '.zip')
                links_filtrados = [url for url in links if url and not url.lower().endswith(extensiones_no_deseadas)]

                todas_urls.extend(links_filtrados)
                paginas_procesadas += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error en página {pagina+1} para '{query}': {e}")
                continue

    todas_urls = list(set(todas_urls))[:60]
    dominios_unicos = list(set(extraer_dominio_base(url) for url in todas_urls))

    return {
        "dominios": dominios_unicos,
        "total_dominios": len(dominios_unicos),
        "variantes_usadas": variantes,
        "paginas_consultadas_total": paginas_procesadas,
        "pais_detectado": codigo_pais
    }

# 🧠 Extrae datos de una URL
@app.post("/extraer_datos")
def extraer_datos_endpoint(
    url: str = Body(..., embed=True),
    pais: str = Body("ES", embed=True),
    usuario = Depends(validar_suscripcion)  # 👈 protección activada
):
    try:
        datos = extraer_datos_desde_url(url, pais)
    except Exception as e:
        datos = {
            "url": url,
            "error": str(e)
        }
    return {
        "resultado": datos,
        "export_payload": {
            "urls": [url],
            "pais": pais
        }
    }

# 🧠 Extrae de múltiples URLs
from datetime import datetime

@app.post("/extraer_multiples")
def extraer_multiples_endpoint(payload: UrlsMultiples, usuario = Depends(validar_suscripcion)):
    start = perf_counter()
    resultados = []

    dominios_unicos = list(set(extraer_dominio_base(url) for url in payload.urls))
    urls_base = [f"https://{dominio}" for dominio in dominios_unicos]

    for dominio in dominios_unicos:
        resultados.append({
            "Dominio": dominio,
            "Fecha": datetime.now().strftime("%Y-%m-%d")
        })

    resp = {
        "resultados": resultados,
        "payload_export": {
            "urls": urls_base,
            "pais": payload.pais
        }
    }
    logger.info(
        "extraer_multiples %d urls en %.2fs", len(payload.urls), perf_counter() - start
    )
    return resp

# 📁 Exportar CSV y guardar historial + leads por nicho normalizado
@app.post("/exportar_csv")
def exportar_csv(payload: ExportarCSVRequest, usuario = Depends(validar_suscripcion), db: Session = Depends(get_db)):
    start = perf_counter()
    nicho_original = payload.nicho
    nicho_normalizado = normalizar_nicho(nicho_original)

    # Obtener dominios únicos normalizados
    dominios_unicos = list(set(extraer_dominio_base(url) for url in payload.urls))

    # Crear filas solo con dominio y fecha
    filas = [{
        "Dominio": dominio,
        "Fecha": datetime.now().strftime("%Y-%m-%d")
    } for dominio in dominios_unicos]

    df = pd.DataFrame(filas)
    df = df.drop_duplicates(subset="Dominio", keep="first")
    df = df.dropna(how="all")

    # No se guarda un CSV permanente. Se generará al vuelo para la descarga.
    df_combinado = df

    # ✅ Guardar en base de datos solo dominios nuevos
    from backend.db import obtener_todos_los_dominios_usuario
    dominios_guardados = obtener_todos_los_dominios_usuario(usuario.email, db)
    dominios_guardados_normalizados = set(normalizar_dominio(d) for d in dominios_guardados)
    nuevos_dominios = [d for d in dominios_unicos if normalizar_dominio(d) not in dominios_guardados_normalizados]

    guardar_leads_extraidos(usuario.email, nuevos_dominios, nicho_normalizado, nicho_original, db)

    # Ya no se mantiene un CSV global. Solo se guardan en la base de datos.

    buffer = BytesIO()
    df_combinado.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)
    logger.info(
        "exportar_csv %s -> %d dominios en %.2fs", nicho_normalizado, len(dominios_unicos), perf_counter() - start
    )
    return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={nicho_original}.csv"})

# 📜 Historial de exportaciones
@app.get("/historial")
def ver_historial(usuario = Depends(get_current_user)):
    historial = obtener_historial(usuario.email)
    return {"historial": historial}

# 📂 Ver nichos del usuario
@app.get("/mis_nichos")
def mis_nichos(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    nichos = obtener_nichos_usuario(usuario.email, db)
    return {"nichos": nichos}

# 🔍 Ver leads por nicho
@app.get("/leads_por_nicho")
def leads_por_nicho(nicho: str, usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    nicho = normalizar_nicho(nicho)
    leads = obtener_leads_por_nicho(usuario.email, nicho, db)
    return {"nicho": nicho, "leads": leads}

@app.get("/exportar_leads_nicho")
def exportar_leads_nicho(nicho: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    start = perf_counter()
    nicho_norm = normalizar_nicho(nicho)
    leads = obtener_leads_por_nicho(usuario.email, nicho_norm, db)

    if not leads:
        raise HTTPException(status_code=404, detail="No hay leads para exportar")

    df = pd.DataFrame([
        {"Dominio": l["url"], "Fecha": l["timestamp"][:10] if l.get("timestamp") else ""}
        for l in leads
    ])

    buffer = BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)
    logger.info(
        "exportar_leads_nicho %s -> %d leads en %.2fs",
        nicho_norm,
        len(df),
        perf_counter() - start,
    )
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nicho}.csv"},
    )

# 🗑️ Eliminar un nicho
@app.delete("/eliminar_nicho")
def eliminar_nicho_usuario(
    nicho: str,
    usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    nicho = normalizar_nicho(nicho)
    eliminar_nicho_postgres(usuario.email, nicho, db)
    return {"mensaje": f"Nicho '{nicho}' eliminado correctamente"}

# ✅ Filtrar URLs repetidas por nicho
class FiltrarUrlsRequest(BaseModel):
    urls: list[str]
    nicho: str

@app.post("/filtrar_urls")
def filtrar_urls(payload: FiltrarUrlsRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    payload.nicho = normalizar_nicho(payload.nicho)
    urls_guardadas = obtener_urls_extraidas_por_nicho(usuario.email, payload.nicho, db)

    dominios_guardados = set(extraer_dominio_base(url) for url in urls_guardadas)
    urls_filtradas = [url for url in payload.urls if extraer_dominio_base(url) not in dominios_guardados]

    return {"urls_filtradas": urls_filtradas}

@app.get("/exportar_todos_mis_leads")
def exportar_todos_mis_leads(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    start = perf_counter()
    from backend.models import LeadExtraido

    leads = (
        db.query(LeadExtraido)
        .filter(LeadExtraido.user_email == usuario.email)
        .order_by(LeadExtraido.timestamp.desc())
        .all()
    )

    if not leads:
        raise HTTPException(status_code=404, detail="No hay leads para exportar")

    df_total = pd.DataFrame([
        {
            "Dominio": lead.url,
            "Nicho": lead.nicho_original,
            "Fecha": str(lead.timestamp)[:10],
        }
        for lead in leads
    ])

    buffer = BytesIO()
    df_total.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)

    nombre_archivo = f"leads_totales_{usuario.email}.csv"
    logger.info(
        "exportar_todos_mis_leads %d leads en %.2fs", len(df_total), perf_counter() - start
    )
    return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"})

class EstadoDominioRequest(BaseModel):
    dominio: str
    estado: str

from sqlalchemy.orm import Session  # asegúrate de tener este import

@app.post("/estado_lead")
def guardar_estado(payload: EstadoDominioRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        url = normalizar_dominio(payload.dominio.strip())
        logger.info(f"Recibido estado='{payload.estado}' para URL='{url}' por usuario='{usuario.email}'")
        guardar_estado_lead(usuario.email, url, payload.estado.strip(), db)
        guardar_evento_historial(usuario.email, url, "estado", f"Estado cambiado a '{payload.estado}'", db)
        return {"mensaje": "Estado actualizado"}
    except Exception as e:
        logger.error(f"ERROR al guardar estado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al guardar estado")

@app.get("/estado_lead")
def obtener_estado(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    url = normalizar_dominio(dominio)
    estado = obtener_estado_lead(usuario.email, url, db)
    return {"estado": estado or "nuevo"}

@app.get("/nichos_de_dominio")
def nichos_de_dominio(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    dominio_base = extraer_dominio_base(dominio)
    nichos = obtener_nichos_para_url(usuario.email, dominio_base, db)
    return {"nichos": nichos}

from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotaDominioRequest(BaseModel):
    dominio: str
    nota: str

@app.post("/nota_lead")
def guardar_nota(payload: NotaDominioRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import guardar_nota_lead_postgres as guardar_nota_lead
    try:
        dominio_base = normalizar_dominio(payload.dominio.strip())
        guardar_nota_lead(usuario.email, dominio_base, payload.nota.strip(), db)
        guardar_evento_historial(usuario.email, dominio_base, "nota", "Nota actualizada", db)
        return {"mensaje": "Nota guardada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar nota: {str(e)}")

@app.get("/nota_lead")
def obtener_nota(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import obtener_nota_lead_postgres as obtener_nota_lead
    dominio_base = normalizar_dominio(dominio)
    nota = obtener_nota_lead(usuario.email, dominio_base, db)

    # Guardar en log
    with open("log_nota_lead.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] Email: {usuario.email} - Dominio: {dominio_base} - Nota encontrada: '{nota}'\n")

    return {"nota": nota or ""}

class InfoExtraRequest(BaseModel):
    dominio: str
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    informacion: Optional[str] = ""

@app.post("/guardar_info_extra")
def guardar_info_extra_api(data: InfoExtraRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import guardar_info_extra_postgres as guardar_info_extra

    dominio = normalizar_dominio(data.dominio.strip())
    guardar_info_extra(
        user_email=usuario.email,
        dominio=dominio,
        email=data.email.strip(),
        telefono=data.telefono.strip(),
        informacion=data.informacion.strip(),
        db=db
    )
    guardar_evento_historial(usuario.email, dominio, "info", "Información extra guardada o actualizada", db)
    return {"mensaje": "Información guardada correctamente"}

@app.get("/info_extra")
def obtener_info_extra_api(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import obtener_info_extra_postgres as obtener_info_extra

    dominio = normalizar_dominio(dominio)
    info = obtener_info_extra(usuario.email, dominio, db)
    return info

@app.get("/buscar_leads")
def buscar_leads(query: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    resultados = buscar_leads_global_postgres(usuario.email, query, db)
    return {"resultados": resultados}

from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

class TareaRequest(BaseModel):
    texto: str
    fecha: Optional[str] = None
    dominio: Optional[str] = None
    tipo: Optional[str] = "lead"
    nicho: Optional[str] = None
    prioridad: Optional[str] = "media"

from backend.db import guardar_tarea_lead_postgres as guardar_tarea_lead
from backend.db import obtener_tareas_lead_postgres as obtener_tareas_lead

@app.post("/tarea_lead")
def agregar_tarea(payload: TareaRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    guardar_tarea_lead(
        email=usuario.email,
        texto=payload.texto.strip(),
        fecha=payload.fecha,
        dominio=payload.dominio.strip() if payload.dominio else None,
        tipo=payload.tipo,
        nicho=payload.nicho.strip() if payload.nicho else None,
        prioridad=payload.prioridad,
        db=db
    )

    # 📌 GUARDAR HISTORIAL SI ES TAREA GENERAL O POR NICHO
    if not payload.dominio:
        guardar_evento_historial(
            usuario.email,
            dominio="general" if payload.tipo == "general" else payload.nicho,
            tipo=payload.tipo,
            descripcion=f"Tarea añadida: {payload.texto}",
            db=db
        )

    # 🧠 GUARDAR HISTORIAL SI ES TAREA POR LEAD
    if payload.dominio:
        guardar_evento_historial(
            usuario.email,
            payload.dominio,
            "tarea",
            f"Tarea añadida: {payload.texto}",
            db=db
        )

    return {"mensaje": "Tarea guardada correctamente"}


@app.get("/tareas_lead")
def ver_tareas(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    tareas = obtener_tareas_lead(usuario.email, normalizar_dominio(dominio), db)
    return {"tareas": tareas}

@app.post("/tarea_completada")
def completar_tarea(tarea_id: int, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    marcar_tarea_completada(usuario.email, tarea_id, db)

    tarea = obtener_tarea_por_id(usuario.email, tarea_id, db)

    if tarea:
        tipo = tarea.get("tipo")
        texto = tarea.get("texto")
        if tipo == "lead":
            guardar_evento_historial(
                usuario.email,
                tarea["dominio"],
                tipo="tarea",
                descripcion=f"Tarea completada: {texto}",
                db=db
            )
        elif tipo == "nicho":
            guardar_evento_historial(
                usuario.email,
                tarea["nicho"],
                tipo="nicho",
                descripcion=f"Tarea completada: {texto}",
                db=db
            )
        elif tipo == "general":
            guardar_evento_historial(
                usuario.email,
                "general",
                tipo="general",
                descripcion=f"Tarea completada: {texto}",
                db=db
            )

    return {"mensaje": "Tarea marcada como completada"}

@app.post("/editar_tarea")
def editar_tarea(tarea_id: int, payload: TareaRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import editar_tarea_existente_postgres as editar_tarea_existente
    editar_tarea_existente(usuario.email, tarea_id, payload, db)
    guardar_evento_historial(
        usuario.email,
        payload.dominio or payload.nicho or "general",
        "tarea",
        f"Tarea editada: {payload.texto}",
        db=db
    )
    return {"mensaje": "Tarea editada correctamente"}

@app.get("/tareas_pendientes")
def tareas_pendientes(usuario=Depends(validar_suscripcion), db: Session = Depends(get_db)):
    tareas = obtener_todas_tareas_pendientes(usuario.email, db)
    return {"tareas": tareas}

@app.get("/historial_lead")
def historial_lead(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    eventos = obtener_historial_por_dominio(usuario.email, normalizar_dominio(dominio), db)
    return {"historial": eventos}

@app.post("/mi_memoria")
def guardar_memoria(request: MemoriaUsuarioRequest, usuario=Depends(get_current_user)):
    try:
        guardar_memoria_usuario(usuario.email, request.descripcion.strip())
        return {"mensaje": "Memoria guardada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar memoria: {str(e)}")

@app.get("/mi_memoria")
def obtener_memoria(usuario=Depends(get_current_user)):
    try:
        memoria = obtener_memoria_usuario(usuario.email)
        return {"memoria": memoria or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener memoria: {str(e)}")

from sqlalchemy.orm import Session

@app.get("/historial_tareas")
def historial_tareas(tipo: str = "general", nicho: str = None, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import obtener_historial_por_tipo_postgres as obtener_historial_por_tipo, obtener_historial_por_nicho_postgres as obtener_historial_por_nicho

    if tipo == "nicho" and nicho:
        historial = obtener_historial_por_nicho(usuario.email, nicho, db)
    else:
        historial = obtener_historial_por_tipo(usuario.email, tipo, db)

    return {"historial": historial}

class CambiarPasswordRequest(BaseModel):
    actual: str
    nueva: str

@app.post("/cambiar_password")
def cambiar_password(
    datos: CambiarPasswordRequest,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verificar_password(datos.actual, usuario.hashed_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")

    usuario.hashed_password = hashear_password(datos.nueva)
    db.add(usuario)
    db.commit()
    return {"mensaje": "Contraseña actualizada correctamente"}

class LeadManualRequest(BaseModel):
    dominio: str
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    nombre: Optional[str] = ""
    nicho: str

@app.post("/añadir_lead_manual")
def añadir_lead_manual(request: LeadManualRequest, usuario=Depends(validar_suscripcion), db: Session = Depends(get_db)):
    try:
        from backend.db import obtener_todos_los_dominios_usuario

        dominio = extraer_dominio_base(request.dominio)
        dominio_normalizado = normalizar_dominio(dominio)

        # Comprobar duplicados globales
        existentes = obtener_todos_los_dominios_usuario(usuario.email, db)
        existentes_normalizados = set(normalizar_dominio(d) for d in existentes)

        if dominio_normalizado in existentes_normalizados:
            raise HTTPException(status_code=400, detail="Este dominio ya existe en tus leads.")

        # Guardar en base de datos
        guardar_leads_extraidos(
            usuario.email,
            [dominio],
            normalizar_nicho(request.nicho),
            request.nicho,
            db
        )

        return {"mensaje": "Lead añadido correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar lead manual: {str(e)}")

from sqlalchemy.orm import Session

@app.post("/importar_csv_manual")
def importar_csv_manual(nicho: str, archivo: UploadFile, usuario=Depends(validar_suscripcion), db: Session = Depends(get_db)):
    contenido = archivo.file.read()
    decoded = contenido.decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)

    filas = []
    dominios = set()

    for fila in reader:
        dominio = extraer_dominio_base(fila.get("Dominio", "").strip())
        if not dominio:
            continue

        filas.append({
            "Dominio": dominio,
            "Nombre": fila.get("Nombre", "").strip(),
            "Emails": fila.get("Email", "").strip(),
            "Teléfonos": fila.get("Teléfono", "").strip(),
            "Instagram": "",
            "Facebook": "",
            "LinkedIn": "",
            "Error": "",
            "Fecha": datetime.now().strftime("%Y-%m-%d")
        })
        dominios.add(dominio)

    df_nuevo = pd.DataFrame(filas)

    guardar_leads_extraidos(usuario.email, list(dominios), normalizar_nicho(nicho), nicho, db)

    return {"mensaje": f"Se han importado {len(dominios)} leads correctamente."}

from pydantic import BaseModel
from sqlalchemy.orm import Session

class MoverLeadRequest(BaseModel):
    dominio: str
    origen: str  # nombre original del nicho
    destino: str  # nombre original del nuevo nicho

@app.post("/mover_lead")
def mover_lead(request: MoverLeadRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import mover_lead_en_bd

    # Toda la lógica se maneja en la base de datos; no se modifican CSVs locales

    # Actualizar en base de datos
    mover_lead_en_bd(
        user_email=usuario.email,
        dominio_original=request.dominio.strip(),
        nicho_origen=normalizar_nicho(request.origen),
        nicho_destino=normalizar_nicho(request.destino),
        nicho_original_destino=request.destino,
        db=db
    )

    return {"mensaje": "Lead movido correctamente"}

from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

class EditarNichoRequest(BaseModel):
    nicho_actual: str
    nuevo_nombre: str

@app.post("/editar_nicho")
def editar_nicho(request: EditarNichoRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import editar_nombre_nicho, guardar_evento_historial
    try:
        editar_nombre_nicho(
            email=usuario.email,
            nicho_actual=request.nicho_actual,
            nuevo_nombre=request.nuevo_nombre,
            db=db
        )

        guardar_evento_historial(
            email=usuario.email,
            dominio="nicho",
            tipo="nicho",
            descripcion=f"Nicho renombrado de '{request.nicho_actual}' a '{request.nuevo_nombre}'",
            db=db
        )

        return {"mensaje": "Nombre del nicho actualizado correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al editar el nicho: {str(e)}")

@app.delete("/eliminar_lead")
def eliminar_lead(
    dominio: str,
    solo_de_este_nicho: bool = True,
    nicho: Optional[str] = None,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import traceback
    from datetime import datetime

    try:
        dominio_base = normalizar_dominio(dominio)

        # 🧪 Log inicial
        with open("log_eliminar_lead.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Inicio eliminación — Email: {usuario.email} — Dominio: {dominio_base} — Solo este nicho: {solo_de_este_nicho} — Nicho: {nicho}\n")

        if solo_de_este_nicho:
            if not nicho:
                raise HTTPException(status_code=400, detail="Debes especificar el nicho.")
            eliminar_lead_de_nicho(usuario.email, dominio_base, normalizar_nicho(nicho), db)
        else:
            eliminar_lead_completamente(usuario.email, dominio_base, db)

        guardar_evento_historial(usuario.email, dominio_base, "lead", "Lead eliminado", db)


        return {"mensaje": "Lead eliminado correctamente"}

    except Exception as e:
        with open("error_eliminar_lead.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] ❌ ERROR INTERNO: {str(e)}\n")
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno al eliminar lead: {str(e)}")

from fastapi import Query, Request  # asegúrate de tener esto al principio
from sqlalchemy.orm import Session
from backend.database import SessionLocal

@app.post("/crear_checkout")
def crear_checkout(
    usuario=Depends(get_current_user),
    plan: str = Query(..., description="ID del plan (price_id) elegido"),
):
    try:
        checkout = stripe.checkout.Session.create(
            customer_email=usuario.email,
            payment_method_types=["card"],
            line_items=[{
                "price": plan,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=os.getenv("STRIPE_SUCCESS_URL"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL"),
        )
        return {"url": checkout.url}
    except Exception as e:
        logger.error(f"ERROR STRIPE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crear_portal_pago")
def crear_portal_pago(
    usuario=Depends(get_current_user),
    plan: str = Query(None, description="ID del plan (price_id) a contratar"),
):
    """Crea una sesión de Checkout o Customer Portal según corresponda."""
    try:
        customers = stripe.Customer.list(email=usuario.email).data
        if customers:
            session = stripe.billing_portal.Session.create(
                customer=customers[0].id,
                return_url=os.getenv("STRIPE_SUCCESS_URL"),
            )
            return {"url": session.url}
        if plan is None:
            raise HTTPException(status_code=400, detail="Plan requerido")
        checkout = stripe.checkout.Session.create(
            customer_email=usuario.email,
            payment_method_types=["card"],
            line_items=[{"price": plan, "quantity": 1}],
            mode="subscription",
            success_url=os.getenv("STRIPE_SUCCESS_URL"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL"),
        )
        return {"url": checkout.url}
    except Exception as e:
        logger.error(f"ERROR STRIPE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crear_portal_cliente")
def crear_portal_cliente(usuario=Depends(get_current_user)):
    """Genera una sesión del portal de facturación de Stripe para que el
    usuario pueda gestionar su suscripción."""
    try:
        customers = stripe.Customer.list(email=usuario.email).data
        if not customers:
            raise HTTPException(
                status_code=404,
                detail="Usuario no tiene cuenta Stripe.",
            )

        session = stripe.billing_portal.Session.create(
            customer=customers[0].id,
            return_url=os.getenv("STRIPE_SUCCESS_URL"),
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"ERROR STRIPE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma no válida")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email")
        nuevo_plan = "pro"

        if customer_email:
            db: Session = SessionLocal()
            try:
                from sqlalchemy import select
                result = db.execute(select(Usuario).where(Usuario.email == customer_email))
                user = result.scalar_one_or_none()
                if user:
                    user.plan = nuevo_plan
                    db.add(user)
                    db.commit()
            finally:
                db.close()

    return {"status": "ok"}

from fastapi import Request
import os

@app.get("/debug-db")
def debug_db(request: Request):
    return {"DATABASE_URL": os.getenv("DATABASE_URL")}