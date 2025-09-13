import os
import json
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, get_openai_client
from streamlit_app.plan_utils import resolve_user_plan, tiene_suscripcion_activa, subscription_cta
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.http_utils import parse_error_message
from streamlit_app.assistant_api import (
    ASSISTANT_EXTRACTION_ENABLED,
    EXTRAER_LEADS_MSG,
    api_buscar,
    api_buscar_variantes_seleccionadas,
)
from streamlit_app.utils.assistant_guard import violates_policy, sanitize_output
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button

st.set_page_config(page_title="Asistente Virtual", page_icon="🤖")

PAGE_NAME = "Asistente"
remember_current_page(PAGE_NAME)
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

token = get_auth_token()
user = st.session_state.get("user")
if token and not user:
    resp_user = http_client.get("/me")
    if isinstance(resp_user, dict) and resp_user.get("_error") == "unauthorized":
        st.warning("Sesión expirada. Vuelve a iniciar sesión.")
        st.stop()
    if getattr(resp_user, "status_code", None) == 200:
        user = resp_user.json()
        st.session_state["user"] = user

with st.sidebar:
    logout_button()

# ────────────────── Config ──────────────────────────
load_dotenv()


def _safe_secret(name: str, default=None):
    """Safely retrieve configuration from env or Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")
client = get_openai_client()

if client is None:
    st.error("El asistente no está disponible: falta OPENAI_API_KEY en el entorno.")
    st.stop()

st.markdown(
    """
    <div style="text-align:center; margin-top: 0.5rem; margin-bottom: 0.5rem;">
        <h2 style="margin-bottom:0.25rem;">Asistente Virtual (Beta)</h2>
        <p>Usa el chat para pedir acciones concretas y consejos. Por Ejemplo: Crea una tarea para no olvidarme de contactar al Lead Opensells.com y escribe un email para contactarle.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

plan = resolve_user_plan(token)["plan"]


def es_intencion_extraer_leads(texto: str) -> bool:
    """Determina si el usuario solicita extraer leads."""
    palabras = [
        "extraer",
        "scrap",
        "scrapear",
        "conseguir leads",
        "generar leads",
        "exportar",
        "descargar",
    ]
    t = texto.lower()
    return any(p in t for p in palabras)


def _respuesta_extraccion_no_disponible():
    """Respuesta unificada cuando la extracción no está disponible."""
    return {"error": EXTRAER_LEADS_MSG}


def _auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle_resp(r):
    """Gestiona respuestas 401/403 mostrando mensajes adecuados."""
    msg = parse_error_message(r)
    if r.status_code == 403:
        st.warning(msg)
        subscription_cta()
    return {"error": msg, "status": r.status_code}


# ────────────────── Funciones de herramientas ─────────────────────
def buscar_leads(query: str):
    try:
        r = http_client.get("/buscar_leads", headers=_auth_headers(), params={"query": query})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        if not http_client.health_ok():
            st.info("Conectando con el backend...")
        return {"error": str(e)}


def obtener_estado_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.get("/estado_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def actualizar_estado_lead(dominio: str, estado: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.post("/estado_lead", headers=_auth_headers(), json={"dominio": dominio, "estado": estado})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def obtener_nota_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.get("/nota_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def actualizar_nota_lead(dominio: str, nota: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.post("/nota_lead", headers=_auth_headers(), json={"dominio": dominio, "nota": nota})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def obtener_tareas_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.get("/tareas_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def api_tarea_general(texto: str, fecha: str | None = None, prioridad: str = "media", tipo: str = "general", nicho: str | None = None):
    payload = {"texto": texto, "prioridad": prioridad, "tipo": tipo, "nicho": nicho, "fecha": fecha}
    if fecha:
        try:
            datetime.fromisoformat(fecha)
        except ValueError:
            return {"error": "fecha_invalida"}
    r = http_client.post("/tarea_lead", json={k: v for k, v in payload.items() if v is not None}, headers=_auth_headers())
    if r.status_code == 200:
        return r.json()
    return {"error": parse_error_message(r), "status": r.status_code}


def crear_tarea_lead(dominio: str, texto: str, fecha: str = None, prioridad: str = "media"):
    payload = {"dominio": dominio, "texto": texto, "prioridad": prioridad, "tipo": "lead", "fecha": fecha}
    if fecha:
        try:
            datetime.fromisoformat(fecha)
        except ValueError:
            return {"error": "fecha_invalida"}
    st.session_state["lead_actual"] = dominio
    r = http_client.post("/tarea_lead", json={k: v for k, v in payload.items() if v is not None}, headers=_auth_headers())
    if r.status_code == 200:
        return r.json()
    return {"error": parse_error_message(r), "status": r.status_code}


def completar_tarea(tarea_id: int):
    try:
        r = http_client.post("/tarea_completada", headers=_auth_headers(), params={"tarea_id": tarea_id})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def historial_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.get("/historial_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def api_mis_nichos():
    r = http_client.get("/mis_nichos", headers=_auth_headers())
    if r.status_code == 200:
        return r.json()
    return {"error": parse_error_message(r), "status": r.status_code}


def obtener_memoria():
    try:
        r = http_client.get("/mi_memoria", headers=_auth_headers())
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def guardar_memoria(descripcion: str):
    try:
        r = http_client.post("/mi_memoria", headers=_auth_headers(), json={"descripcion": descripcion})
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def _tool_api_buscar(cliente_ideal: str, forzar_variantes: bool = False, contexto_extra: str | None = None):
    return api_buscar(cliente_ideal, forzar_variantes=forzar_variantes, contexto_extra=contexto_extra, headers=_auth_headers())


def _tool_api_buscar_variantes_seleccionadas(variantes: list[str]):
    return api_buscar_variantes_seleccionadas(variantes, headers=_auth_headers())


def api_extraer_multiples(urls: list[str], pais: str = "ES"):
    """Stub de extracción para evitar llamadas reales al backend."""
    return _respuesta_extraccion_no_disponible()


def api_exportar_csv(urls: list[str], pais: str = "ES", nicho: str = ""):
    """Exportar CSV deshabilitado mientras la extracción no está disponible."""
    return _respuesta_extraccion_no_disponible()


def api_leads_por_nicho(nicho: str):
    r = http_client.get(f"/leads_por_nicho?nicho={nicho}", headers=_auth_headers())
    if r.status_code == 200:
        return r.json()
    return {"error": parse_error_message(r), "status": r.status_code}


def mover_lead(dominio: str, origen: str, destino: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.post(
            "/mover_lead",
            headers=_auth_headers(),
            json={"dominio": dominio, "origen": origen, "destino": destino},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def editar_nicho(nicho_actual: str, nuevo_nombre: str):
    try:
        r = http_client.post(
            "/editar_nicho",
            headers=_auth_headers(),
            json={"nicho_actual": nicho_actual, "nuevo_nombre": nuevo_nombre},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def eliminar_nicho(nicho: str):
    try:
        r = http_client.delete(
            "/eliminar_nicho",
            headers=_auth_headers(),
            params={"nicho": nicho},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def eliminar_lead(dominio: str, solo_de_este_nicho: bool = True, nicho: str | None = None):
    st.session_state["lead_actual"] = dominio
    params = {"dominio": dominio, "solo_de_este_nicho": solo_de_este_nicho}
    if nicho:
        params["nicho"] = nicho
    try:
        r = http_client.delete("/eliminar_lead", headers=_auth_headers(), params=params)
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def historial_tareas(tipo: str = "general", nicho: str | None = None):
    params = {"tipo": tipo}
    if nicho:
        params["nicho"] = nicho
    try:
        r = http_client.get("/historial_tareas", headers=_auth_headers(), params=params)
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def api_tareas_pendientes():
    r = http_client.get("/tareas_pendientes", headers=_auth_headers())
    if r.status_code == 200:
        return r.json()
    if r.status_code == 403:
        st.warning("Tu plan no permite ver tareas pendientes desde esta vista")
        subscription_cta()
    return {"error": parse_error_message(r), "status": r.status_code}


def _render_lead_actions():
    dominio = st.session_state.get("lead_actual")
    if not dominio:
        return
    c1, c2, c3 = st.columns(3)

    # Ver tareas
    ver_key = f"show_tareas_{dominio}"
    if c1.button("Ver tareas de este lead", key=f"ver_tareas_{dominio}"):
        st.session_state[ver_key] = not st.session_state.get(ver_key, False)
    if st.session_state.get(ver_key, False):
        tareas = obtener_tareas_lead(dominio)
        if tareas.get("error"):
            c1.error(tareas["error"])
        else:
            for t in tareas.get("tareas", []):
                c1.write(f"- {t.get('texto')} ({t.get('prioridad')})")
                if c1.button("Completar", key=f"compl_{t.get('id')}"):
                    res = completar_tarea(t.get("id"))
                    if res.get("error"):
                        c1.error(res["error"])
                    else:
                        c1.success("Tarea completada")

    # Añadir nota
    nota_key = f"show_nota_{dominio}"
    if c2.button("Añadir nota", key=f"add_nota_{dominio}"):
        st.session_state[nota_key] = not st.session_state.get(nota_key, False)
    if st.session_state.get(nota_key, False):
        with c2.form(key=f"nota_form_{dominio}"):
            nota = st.text_area("Nota", key=f"nota_{dominio}")
            submitted = st.form_submit_button("Guardar nota")
            if submitted:
                res = actualizar_nota_lead(dominio, nota)
                if res.get("error"):
                    c2.error(res["error"])
                else:
                    st.toast("Nota guardada")
                    st.session_state[nota_key] = False

    # Cambiar estado
    estado_key = f"show_estado_{dominio}"
    if c3.button("Cambiar estado", key=f"cambiar_estado_{dominio}"):
        st.session_state[estado_key] = not st.session_state.get(estado_key, False)
    if st.session_state.get(estado_key, False):
        with c3.form(key=f"estado_form_{dominio}"):
            estado = st.selectbox(
                "Nuevo estado",
                ["nuevo", "contactado", "en_proceso", "cliente", "descartado"],
                key=f"estado_{dominio}",
            )
            submitted = st.form_submit_button("Guardar estado")
            if submitted:
                res = actualizar_estado_lead(dominio, estado)
                if res.get("error"):
                    c3.error(res["error"])
                else:
                    st.toast("Estado actualizado")
                    st.session_state[estado_key] = False


TOOLS = {
    "buscar_leads": buscar_leads,
    "api_buscar": _tool_api_buscar,
    "api_buscar_variantes_seleccionadas": _tool_api_buscar_variantes_seleccionadas,
    "api_extraer_multiples": api_extraer_multiples,
    "api_exportar_csv": api_exportar_csv,
    "obtener_estado_lead": obtener_estado_lead,
    "actualizar_estado_lead": actualizar_estado_lead,
    "obtener_nota_lead": obtener_nota_lead,
    "actualizar_nota_lead": actualizar_nota_lead,
    "obtener_tareas_lead": obtener_tareas_lead,
    "api_tarea_general": api_tarea_general,
    "crear_tarea_lead": crear_tarea_lead,
    "completar_tarea": completar_tarea,
    "historial_lead": historial_lead,
    "api_mis_nichos": api_mis_nichos,
    "api_leads_por_nicho": api_leads_por_nicho,
    "mover_lead": mover_lead,
    "editar_nicho": editar_nicho,
    "eliminar_nicho": eliminar_nicho,
    "eliminar_lead": eliminar_lead,
    "historial_tareas": historial_tareas,
    "api_tareas_pendientes": api_tareas_pendientes,
    "obtener_memoria": obtener_memoria,
    "guardar_memoria": guardar_memoria,
}


tool_defs = [
    {
        "type": "function",
        "function": {
            "name": "api_buscar",
            "description": "Genera variantes de búsqueda para un cliente ideal",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_ideal": {"type": "string"},
                    "forzar_variantes": {"type": "boolean"},
                    "contexto_extra": {"type": "string"},
                },
                "required": ["cliente_ideal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_buscar_variantes_seleccionadas",
            "description": "Obtiene dominios a partir de variantes seleccionadas",
            "parameters": {
                "type": "object",
                "properties": {"variantes": {"type": "array", "items": {"type": "string"}}},
                "required": ["variantes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_extraer_multiples",
            "description": "Extrae datos básicos de múltiples URLs",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {"type": "array", "items": {"type": "string"}},
                    "pais": {"type": "string"},
                },
                "required": ["urls"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_exportar_csv",
            "description": "Exporta un conjunto de URLs a CSV y guarda los leads",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {"type": "array", "items": {"type": "string"}},
                    "nicho": {"type": "string"},
                    "pais": {"type": "string"},
                },
                "required": ["urls", "nicho"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_leads",
            "description": "Buscar leads por texto o dominio",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_estado_lead",
            "description": "Obtiene el estado actual de un lead",
            "parameters": {
                "type": "object",
                "properties": {"dominio": {"type": "string"}},
                "required": ["dominio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_estado_lead",
            "description": "Actualiza el estado de un lead",
            "parameters": {
                "type": "object",
                "properties": {
                    "dominio": {"type": "string"},
                    "estado": {"type": "string"},
                },
                "required": ["dominio", "estado"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_nota_lead",
            "description": "Obtiene la nota guardada para un lead",
            "parameters": {
                "type": "object",
                "properties": {"dominio": {"type": "string"}},
                "required": ["dominio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_nota_lead",
            "description": "Guarda o actualiza una nota para un lead",
            "parameters": {
                "type": "object",
                "properties": {
                    "dominio": {"type": "string"},
                    "nota": {"type": "string"},
                },
                "required": ["dominio", "nota"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_tareas_lead",
            "description": "Lista tareas pendientes de un lead",
            "parameters": {
                "type": "object",
                "properties": {"dominio": {"type": "string"}},
                "required": ["dominio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_tarea_lead",
            "description": "Crea una nueva tarea para un lead",
            "parameters": {
                "type": "object",
                "properties": {
                    "dominio": {"type": "string"},
                    "texto": {"type": "string"},
                    "fecha": {"type": "string"},
                    "prioridad": {"type": "string"},
                },
                "required": ["dominio", "texto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_tarea_general",
            "description": "Crea una tarea general o por nicho",
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string"},
                    "fecha": {"type": "string"},
                    "prioridad": {"type": "string"},
                    "tipo": {"type": "string"},
                    "nicho": {"type": "string"},
                },
                "required": ["texto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "completar_tarea",
            "description": "Marca una tarea como completada",
            "parameters": {
                "type": "object",
                "properties": {"tarea_id": {"type": "integer"}},
                "required": ["tarea_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historial_lead",
            "description": "Recupera el historial de un lead",
            "parameters": {
                "type": "object",
                "properties": {"dominio": {"type": "string"}},
                "required": ["dominio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_mis_nichos",
            "description": "Devuelve los nichos del usuario",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_leads_por_nicho",
            "description": "Obtiene los leads almacenados en un nicho",
            "parameters": {
                "type": "object",
                "properties": {"nicho": {"type": "string"}},
                "required": ["nicho"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mover_lead",
            "description": "Mueve un lead de un nicho a otro",
            "parameters": {
                "type": "object",
                "properties": {
                    "dominio": {"type": "string"},
                    "origen": {"type": "string"},
                    "destino": {"type": "string"},
                },
                "required": ["dominio", "origen", "destino"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "editar_nicho",
            "description": "Edita el nombre de un nicho",
            "parameters": {
                "type": "object",
                "properties": {
                    "nicho_actual": {"type": "string"},
                    "nuevo_nombre": {"type": "string"},
                },
                "required": ["nicho_actual", "nuevo_nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_nicho",
            "description": "Elimina un nicho completo",
            "parameters": {
                "type": "object",
                "properties": {"nicho": {"type": "string"}},
                "required": ["nicho"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_lead",
            "description": "Elimina un lead opcionalmente solo de un nicho",
            "parameters": {
                "type": "object",
                "properties": {
                    "dominio": {"type": "string"},
                    "solo_de_este_nicho": {"type": "boolean"},
                    "nicho": {"type": "string"},
                },
                "required": ["dominio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historial_tareas",
            "description": "Historial de tareas filtrado",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string"},
                    "nicho": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "api_tareas_pendientes",
            "description": "Obtiene todas las tareas pendientes del usuario",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_memoria",
            "description": "Obtiene la memoria guardada del usuario",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_memoria",
            "description": "Guarda un recordatorio en la memoria del usuario",
            "parameters": {
                "type": "object",
                "properties": {"descripcion": {"type": "string"}},
                "required": ["descripcion"],
            },
        },
    },
]


def build_system_prompt() -> str:
    nichos = cached_get("/mis_nichos", token).get("nichos", [])
    tareas = cached_get("tareas_pendientes", token) or []
    resumen_nichos = ", ".join(n["nicho_original"] for n in nichos) or "ninguno"
    resumen_tareas = f"Tienes {len(tareas)} tareas pendientes."
    return (
        "Eres un asistente conectado a herramientas. Cuando el usuario pida BUSCAR o EXTRAER leads, "
        "SIEMPRE sigue este pipeline con tools y sin inventar nada:\n"
        "1) api_buscar(cliente_ideal) → si devuelve 'pregunta_sugerida', haz como máximo 2 preguntas breves.\n"
        "2) api_buscar_variantes_seleccionadas(elige 3 variantes relevantes).\n"
        "3) api_extraer_multiples(urls, pais detectado o 'ES' por defecto).\n"
        "4) api_exportar_csv(urls, pais, nicho) → ofrece botón de descarga.\n"
        "Si el plan es free y una acción premium devuelve 403, informa y muestra CTA.\n"
        "Para tareas/estados/notas/historial usa las tools específicas.\n\n"
        f"Nichos del usuario: {resumen_nichos}.\n{resumen_tareas}"
    )


# ────────────────── Conversación ────────────────────
MAX_TURNS = 20
if "chat" not in st.session_state:
    st.session_state.chat = []
elif len(st.session_state.chat) > MAX_TURNS * 2:
    history = st.session_state.chat[:-MAX_TURNS * 2]
    try:
        resumen = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": "Resume brevemente esta conversación: " + json.dumps(history, ensure_ascii=False),
                }
            ],
        ).choices[0].message.content
        st.session_state.chat = (
            [{"role": "system", "content": f"Resumen previo: {resumen}"}] + st.session_state.chat[-MAX_TURNS * 2:]
        )
    except Exception:
        st.session_state.chat = st.session_state.chat[-MAX_TURNS * 2:]

for entrada in st.session_state.chat:
    if entrada["role"] in ("user", "assistant"):
        with st.chat_message(entrada["role"]):
            st.markdown(entrada["content"])

pregunta = st.chat_input("Haz una pregunta sobre tus nichos, leads o tareas...")

if pregunta:
    blocked, msg_pol = violates_policy(pregunta, context="project")
    if blocked:
        with st.chat_message("assistant"):
            st.write(msg_pol)
        st.session_state.chat.append({"role": "assistant", "content": msg_pol})
        st.stop()
    st.session_state.pop("csv_bytes", None)
    st.session_state.pop("csv_filename", None)
    st.session_state.chat.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    if es_intencion_extraer_leads(pregunta) and not ASSISTANT_EXTRACTION_ENABLED:
        content = EXTRAER_LEADS_MSG
        st.session_state.chat.append({"role": "assistant", "content": content})
        with st.chat_message("assistant"):
            st.markdown(content)
        st.stop()
    else:
        if not tiene_suscripcion_activa(plan):
            st.info(
                "Puedes chatear y gestionar información básica. Para EXTRAER o EXPORTAR leads necesitas un plan activo."
            )
            subscription_cta()

        contexto = build_system_prompt()
        keywords = ["extraer", "conseguir", "buscar", "crear nicho", "exportar"]
        if any(k in pregunta.lower() for k in keywords):
            contexto += f"\nObjetivo del usuario: {pregunta}"
        messages = [{"role": "system", "content": contexto}] + st.session_state.chat

        with st.spinner("Pensando..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tool_defs,
                    tool_choice="auto",
                )
                msg = response.choices[0].message
                while getattr(msg, "tool_calls", None):
                    st.session_state.chat.append(
                        {"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls}
                    )
                    for tc in msg.tool_calls:
                        func = TOOLS.get(tc.function.name)
                        args = json.loads(tc.function.arguments or "{}")
                        resultado = func(**args) if func else {"error": f"Tool {tc.function.name} no disponible"}
                        st.session_state.chat.append(
                            {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(resultado, ensure_ascii=False)}
                        )
                    messages = [{"role": "system", "content": contexto}] + st.session_state.chat
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        tools=tool_defs,
                        tool_choice="auto",
                    )
                    msg = response.choices[0].message
            except Exception:
                st.warning("El servidor de IA está ocupado. Inténtalo de nuevo en unos segundos.")
                st.stop()

        content = sanitize_output(msg.content or "", context="project")
        blocked_out, msg_pol_out = violates_policy(content, context="project")
        if blocked_out:
            content = msg_pol_out
        st.session_state.chat.append({"role": "assistant", "content": content})
        with st.chat_message("assistant"):
            st.markdown(content)
            if not blocked_out:
                _render_lead_actions()
                if st.session_state.get("csv_bytes"):
                    st.download_button(
                        "⬇️ Descargar CSV",
                        st.session_state.get("csv_bytes"),
                        file_name=st.session_state.get("csv_filename", "leads.csv"),
                        mime="text/csv",
                        use_container_width=True,
                    )

