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
from pydantic import BaseModel
from fastapi import FastAPI, Body, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import requests
from fastapi.responses import FileResponse
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import unicodedata
import re
from fastapi.responses import StreamingResponse
from io import BytesIO
import asyncio

# Cargar variables de entorno antes de usar Stripe
load_dotenv()

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
    eliminar_nicho,
    obtener_urls_extraidas_por_nicho,
)

from backend.db import guardar_estado_lead, obtener_estado_lead
from sqlalchemy.orm import Session
from backend.db import obtener_nichos_para_url

load_dotenv()

app = FastAPI()

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

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
        print(f"\n🔍 Procesando variante: '{query}'")

        for pagina in range(paginas_por_variante):
            start = pagina * resultados_por_pagina
            print(f"➡️ Página {pagina+1} (start={start})")

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
                print(f"❌ Error en página {pagina+1} para '{query}': {e}")
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
    resultados = []

    dominios_unicos = list(set(extraer_dominio_base(url) for url in payload.urls))
    urls_base = [f"https://{dominio}" for dominio in dominios_unicos]

    for dominio in dominios_unicos:
        resultados.append({
            "Dominio": dominio,
            "Fecha": datetime.now().strftime("%Y-%m-%d")
        })

    return {
        "resultados": resultados,
        "payload_export": {
            "urls": urls_base,
            "pais": payload.pais
        }
    }

# 📁 Exportar CSV y guardar historial + leads por nicho normalizado
@app.post("/exportar_csv")
async def exportar_csv(payload: ExportarCSVRequest, usuario = Depends(validar_suscripcion), db: Session = Depends(get_db)):
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

    # Guardar CSV por nicho
    carpeta_usuario = os.path.join("exports", usuario.email)
    os.makedirs(carpeta_usuario, exist_ok=True)
    archivo_usuario_nicho = os.path.join(carpeta_usuario, f"{nicho_normalizado}.csv")

    if os.path.exists(archivo_usuario_nicho):
        try:
            df_existente = pd.read_csv(archivo_usuario_nicho)
        except pd.errors.EmptyDataError:
            df_existente = pd.DataFrame(columns=["Dominio", "Fecha"])
        df_combinado = pd.concat([df_existente, df], ignore_index=True)
        df_combinado.drop_duplicates(subset="Dominio", inplace=True)
    else:
        df_combinado = df

    df_combinado.to_csv(archivo_usuario_nicho, index=False, encoding="utf-8-sig")

    # ✅ Guardar en base de datos solo dominios nuevos
    from backend.db import obtener_todos_los_dominios_usuario
    dominios_guardados = await obtener_todos_los_dominios_usuario(usuario.email, db)
    dominios_guardados_normalizados = set(normalizar_dominio(d) for d in dominios_guardados)
    nuevos_dominios = [d for d in dominios_unicos if normalizar_dominio(d) not in dominios_guardados_normalizados]

    await guardar_leads_extraidos(usuario.email, nuevos_dominios, nicho_normalizado, nicho_original)

    # Guardar CSV global para admin
    os.makedirs("admin_data", exist_ok=True)
    archivo_global = os.path.join("admin_data", "todos_los_leads.csv")
    df["Usuario"] = usuario.email

    if os.path.exists(archivo_global):
        try:
            df_global = pd.read_csv(archivo_global)
        except pd.errors.EmptyDataError:
            df_global = pd.DataFrame(columns=["Dominio", "Fecha", "Usuario"])
        combinado_global = pd.concat([df_global, df], ignore_index=True)
        combinado_global.drop_duplicates(subset="Dominio", inplace=True)
    else:
        combinado_global = df

    combinado_global.to_csv(archivo_global, index=False, encoding="utf-8-sig")

    return FileResponse(archivo_usuario_nicho, filename=f"{nicho_original}.csv", media_type="text/csv")

# 📜 Historial de exportaciones
@app.get("/historial")
async def ver_historial(usuario = Depends(get_current_user)):
    historial = await obtener_historial(usuario.email)
    return {"historial": historial}

# 📂 Ver nichos del usuario
@app.get("/mis_nichos")
def mis_nichos(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    nichos = obtener_nichos_usuario(usuario.email, db)
    return {"nichos": nichos}

# 🔍 Ver leads por nicho
@app.get("/leads_por_nicho")
async def leads_por_nicho(nicho: str, usuario = Depends(get_current_user)):
    nicho = normalizar_nicho(nicho)
    leads = await obtener_leads_por_nicho(usuario.email, nicho)
    return {"nicho": nicho, "leads": leads}

# 🗑️ Eliminar un nicho
@app.delete("/eliminar_nicho")
async def eliminar_nicho_usuario(nicho: str, usuario = Depends(get_current_user)):
    nicho = normalizar_nicho(nicho)
    await eliminar_nicho(usuario.email, nicho)
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
async def exportar_todos_mis_leads(usuario=Depends(get_current_user)):
    carpeta_usuario = os.path.join("exports", usuario.email)
    if not os.path.exists(carpeta_usuario):
        raise HTTPException(status_code=404, detail="No hay leads para exportar")

    archivos_csv = [os.path.join(carpeta_usuario, f) for f in os.listdir(carpeta_usuario) if f.endswith(".csv")]
    if not archivos_csv:
        raise HTTPException(status_code=404, detail="No hay archivos CSV para exportar")

    df_total = pd.concat([pd.read_csv(archivo) for archivo in archivos_csv], ignore_index=True)
    df_total.drop_duplicates(subset="Dominio", inplace=True)

    buffer = BytesIO()
    df_total.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)

    nombre_archivo = f"leads_totales_{usuario.email}.csv"
    return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"})

class EstadoDominioRequest(BaseModel):
    dominio: str
    estado: str

from sqlalchemy.orm import Session  # asegúrate de tener este import

@app.post("/estado_lead")
def guardar_estado(payload: EstadoDominioRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        url = normalizar_dominio(payload.dominio.strip())
        print(f"📩 Recibido estado='{payload.estado}' para URL='{url}' por usuario='{usuario.email}'")
        guardar_estado_lead(usuario.email, url, payload.estado.strip(), db)
        guardar_evento_historial(usuario.email, url, "estado", f"Estado cambiado a '{payload.estado}'", db)
        return {"mensaje": "Estado actualizado"}
    except Exception as e:
        print(f"❌ ERROR al guardar estado: {str(e)}")
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
    email_contacto: Optional[str] = ""
    telefono: Optional[str] = ""
    info_adicional: Optional[str] = ""

@app.post("/guardar_info_extra")
def guardar_info_extra_api(data: InfoExtraRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.db import guardar_info_extra_postgres as guardar_info_extra

    dominio = normalizar_dominio(data.dominio.strip())
    guardar_info_extra(
        email=usuario.email,
        dominio=dominio,
        email_contacto=data.email_contacto.strip(),
        telefono=data.telefono.strip(),
        info_adicional=data.info_adicional.strip(),
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
    resultados = buscar_leads_global(usuario.email, query, db)
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
def tareas_pendientes(usuario=Depends(get_current_user)):
    tareas = obtener_todas_tareas_pendientes(usuario.email)
    return {"tareas": tareas}

@app.get("/historial_lead")
def historial_lead(dominio: str, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    eventos = obtener_historial_por_dominio(usuario.email, normalizar_dominio(dominio), db)
    return {"historial": eventos}

@app.post("/mi_memoria")
def guardar_memoria(request: MemoriaUsuarioRequest, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        guardar_memoria_usuario(usuario.email, request.descripcion.strip(), db)
        return {"mensaje": "Memoria guardada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar memoria: {str(e)}")

@app.get("/mi_memoria")
def obtener_memoria(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        memoria = obtener_memoria_usuario(usuario.email, db)
        return {"memoria": memoria}
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
        existentes_normalizados = set([normalizar_dominio(d) for d in existentes])

        if dominio_normalizado in existentes_normalizados:
            raise HTTPException(status_code=400, detail="Este dominio ya existe en tus leads.")

        # Guardar CSV por nicho
        fila = {
            "Dominio": dominio,
            "Fecha": datetime.now().strftime("%Y-%m-%d")
        }

        carpeta_usuario = os.path.join("exports", usuario.email)
        os.makedirs(carpeta_usuario, exist_ok=True)
        archivo_usuario_nicho = os.path.join(carpeta_usuario, f"{normalizar_nicho(request.nicho)}.csv")

        if os.path.exists(archivo_usuario_nicho):
            df_existente = pd.read_csv(archivo_usuario_nicho)
            df_combinado = pd.concat([df_existente, pd.DataFrame([fila])], ignore_index=True)
            df_combinado.drop_duplicates(subset="Dominio", inplace=True)
        else:
            df_combinado = pd.DataFrame([fila])

        df_combinado.to_csv(archivo_usuario_nicho, index=False, encoding="utf-8-sig")

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

    carpeta_usuario = os.path.join("exports", usuario.email)
    os.makedirs(carpeta_usuario, exist_ok=True)
    archivo_usuario_nicho = os.path.join(carpeta_usuario, f"{normalizar_nicho(nicho)}.csv")

    if os.path.exists(archivo_usuario_nicho):
        df_existente = pd.read_csv(archivo_usuario_nicho)
        df_combinado = pd.concat([df_existente, df_nuevo], ignore_index=True)
        df_combinado.drop_duplicates(subset="Dominio", inplace=True)
    else:
        df_combinado = df_nuevo

    df_combinado.to_csv(archivo_usuario_nicho, index=False, encoding="utf-8-sig")

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

    carpeta_usuario = os.path.join("exports", usuario.email)
    archivo_origen = os.path.join(carpeta_usuario, f"{normalizar_nicho(request.origen)}.csv")
    archivo_destino = os.path.join(carpeta_usuario, f"{normalizar_nicho(request.destino)}.csv")

    if not os.path.exists(archivo_origen):
        raise HTTPException(status_code=404, detail="Nicho de origen no encontrado.")

    df_origen = pd.read_csv(archivo_origen)

    if "Dominio" not in df_origen.columns:
        raise HTTPException(status_code=400, detail="El archivo de origen no tiene la columna 'Dominio'.")

    dominio_buscado = request.dominio.strip().lower().replace("www.", "")

    df_origen["Dominio_normalizado"] = (
        df_origen["Dominio"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace("www.", "", regex=False)
    )

    lead_fila = df_origen[df_origen["Dominio_normalizado"] == dominio_buscado]

    if lead_fila.empty:
        raise HTTPException(status_code=404, detail=f"El lead '{dominio_buscado}' no se encuentra en el nicho de origen.")

    # Actualizar CSV
    df_origen = df_origen[df_origen["Dominio_normalizado"] != dominio_buscado]

    if df_origen.empty:
        os.remove(archivo_origen)
    else:
        df_origen.drop(columns=["Dominio_normalizado"], inplace=True)
        df_origen.to_csv(archivo_origen, index=False, encoding="utf-8-sig")

    if os.path.exists(archivo_destino):
        df_destino = pd.read_csv(archivo_destino)
    else:
        df_destino = pd.DataFrame()

    lead_fila = lead_fila.drop(columns=["Dominio_normalizado"])
    df_destino = pd.concat([df_destino, lead_fila], ignore_index=True)
    df_destino.to_csv(archivo_destino, index=False, encoding="utf-8-sig")

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

        # Renombrar archivo CSV si existe
        carpeta_usuario = os.path.join("exports", usuario.email)
        nicho_antiguo_norm = normalizar_nicho(request.nicho_actual)
        nicho_nuevo_norm = normalizar_nicho(request.nuevo_nombre)

        nombre_antiguo = os.path.join(carpeta_usuario, f"{nicho_antiguo_norm}.csv")
        nombre_nuevo = os.path.join(carpeta_usuario, f"{nicho_nuevo_norm}.csv")

        with open("debug_renombrar_csv.log", "a", encoding="utf-8") as f:
            f.write(f"Intentando renombrar: {nombre_antiguo} → {nombre_nuevo}\n")

        if os.path.exists(nombre_antiguo):
            os.rename(nombre_antiguo, nombre_nuevo)
        else:
            with open("debug_renombrar_csv.log", "a", encoding="utf-8") as f:
                f.write("❌ Archivo original no encontrado.\n")

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

        # 🔥 También eliminar del CSV correspondiente
        carpeta_usuario = os.path.join("exports", usuario.email)
        if solo_de_este_nicho and nicho:
            archivo_csv = os.path.join(carpeta_usuario, f"{normalizar_nicho(nicho)}.csv")
            if os.path.exists(archivo_csv):
                try:
                    df = pd.read_csv(archivo_csv)
                    df["Dominio_normalizado"] = (
                        df["Dominio"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        .str.replace("www.", "", regex=False)
                    )
                    df = df[df["Dominio_normalizado"] != dominio_base]
                    df.drop(columns=["Dominio_normalizado"], inplace=True)
                    df.to_csv(archivo_csv, index=False, encoding="utf-8-sig")
                except Exception as e:
                    with open("log_eliminar_lead.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] ❌ Error al modificar CSV único: {str(e)}\n")
        else:
            if os.path.exists(carpeta_usuario):
                archivos_csv = [f for f in os.listdir(carpeta_usuario) if f.endswith(".csv")]
                for archivo in archivos_csv:
                    archivo_csv = os.path.join(carpeta_usuario, archivo)
                    try:
                        df = pd.read_csv(archivo_csv)
                        df["Dominio_normalizado"] = (
                            df["Dominio"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            .str.replace("www.", "", regex=False)
                        )
                        df = df[df["Dominio_normalizado"] != dominio_base]
                        df.drop(columns=["Dominio_normalizado"], inplace=True)
                        df.to_csv(archivo_csv, index=False, encoding="utf-8-sig")
                    except Exception as e:
                        with open("log_eliminar_lead.txt", "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] ❌ Error al modificar CSV global: {str(e)}\n")

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
    plan: str = Query(..., description="ID del plan (price_id) elegido")
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
        print(f"❌ ERROR STRIPE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portal_cliente")
def portal_cliente(usuario=Depends(get_current_user)):
    try:
        customers = stripe.Customer.list(email=usuario.email).data
        if not customers:
            raise HTTPException(status_code=404, detail="Usuario no tiene cuenta Stripe.")

        session = stripe.billing_portal.Session.create(
            customer=customers[0].id,
            return_url=os.getenv("STRIPE_SUCCESS_URL"),
        )
        return {"url": session.url}
    except Exception as e:
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