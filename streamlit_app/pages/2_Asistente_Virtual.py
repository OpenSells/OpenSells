import os
import json
import re
import unicodedata
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, get_openai_client
from streamlit_app.plan_utils import subscription_cta
import streamlit_app.utils.http_client as http_client
from streamlit_app.assistant_api import (
    EXTRAER_LEADS_MSG,
    api_buscar,
    api_buscar_variantes_seleccionadas,
)
from streamlit_app.utils.assistant_guard import violates_policy, sanitize_output
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button
from components.ui import render_whatsapp_fab

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

def es_intencion_extraer_leads(texto: str) -> bool:
    """Determina si el usuario solicita extraer o exportar leads."""
    palabras = [
        "extraer",
        "extracción",
        "extrae",
        "scrap",
        "scrapear",
        "conseguir leads",
        "generar leads",
        "exportar",
        "exportación",
        "csv",
        "descargar csv",
        "descargar leads",
    ]
    t = texto.lower()
    return any(p in t for p in palabras)


def _extraccion_msg() -> str:
    """Devuelve el mensaje oficial para solicitudes de extracción/exportación."""
    msg = EXTRAER_LEADS_MSG
    if isinstance(msg, dict):
        msg = msg.get("text") or msg.get("message") or ""
    if not isinstance(msg, str) or not msg.strip():
        msg = (
            "🏗️ Esta funcionalidad desde el asistente estará disponible próximamente. "
            "Mientras tanto, puedes usar la página de Búsqueda para generar leads."
        )
    return msg


def _slugify_nicho(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    t = texto.strip().lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("utf-8")
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")


def _build_nicho_maps() -> tuple[dict, dict]:
    """
    Devuelve (pretty_to_slug, slug_to_pretty) a partir de /mis_nichos.
    - pretty: n['nicho_original'] o fallback n['nicho'] (visible)
    - slug:   n['nicho'] (clave normalizada en backend)
    """
    data = api_mis_nichos() if callable(api_mis_nichos) else {}
    nichos = data.get("nichos", []) if isinstance(data, dict) else (data or [])
    p2s, s2p = {}, {}
    for n in nichos:
        slug = (n.get("nicho") or "").strip()
        pretty = (n.get("nicho_original") or n.get("nicho") or "").strip()
        if slug:
            p2s[pretty] = slug
            s2p[slug] = pretty
    return p2s, s2p


def _resolve_nicho_slug(nicho_user: str | None) -> str | None:
    """
    Acepta nombres con espacios/mayúsculas/tildes y devuelve el slug existente.
    - Coincide por:
      1) slug exacto
      2) pretty exacto
      3) slugify del input contra slug existente
    """
    if not nicho_user:
        return None
    p2s, s2p = _build_nicho_maps()
    raw = nicho_user.strip()
    if raw in s2p:
        return raw
    if raw in p2s:
        return p2s[raw]
    candidate = _slugify_nicho(raw)
    return candidate if candidate in s2p else None


def _refresh_mis_nichos_cache():
    """Fuerza lectura directa del backend y guarda en session para que el prompt use datos frescos."""
    try:
        r = http_client.get("/mis_nichos", headers=_auth_headers())
        if getattr(r, "status_code", None) == 200:
            data = r.json()
            st.session_state["mis_nichos_fresh"] = data if isinstance(data, list) else data.get("nichos", [])
        else:
            st.session_state.pop("mis_nichos_fresh", None)
    except Exception:
        st.session_state.pop("mis_nichos_fresh", None)


def _count_leads_in_nicho(slug: str) -> int:
    try:
        r = http_client.get("/leads_por_nicho", headers=_auth_headers(), params={"nicho": slug})
        if getattr(r, "status_code", None) == 200:
            data = r.json() or {}
            if isinstance(data, dict):
                if "count" in data and isinstance(data["count"], int):
                    return data["count"]
                items = data.get("items")
                if isinstance(items, list):
                    return len(items)
        return 0
    except Exception:
        return -1


def _fetch_mis_nichos_fresh() -> list:
    try:
        r = http_client.get("/mis_nichos", headers=_auth_headers())
        if getattr(r, "status_code", None) == 200:
            data = r.json()
            lst = data if isinstance(data, list) else data.get("nichos", [])
            return lst or []
    except Exception:
        pass
    return []


def _auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle_resp(r):
    """Gestiona respuestas 401/403 mostrando mensajes adecuados."""
    if r.status_code == 403:
        st.warning("Tu plan no permite esta acción.")
        subscription_cta()
    return {"error": r.text, "status": r.status_code}


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
        r = http_client.get("/info_extra", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            data = r.json()
            nota = ""
            if isinstance(data, dict):
                nota = data.get("informacion", "")
            return {"nota": nota}
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def actualizar_nota_lead(dominio: str, nota: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.post(
            "/guardar_info_extra",
            headers=_auth_headers(),
            json={"dominio": dominio, "informacion": nota},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def obtener_tareas_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_client.get(
            "/tareas",
            headers=_auth_headers(),
            params={"tipo": "lead", "dominio": dominio, "solo_pendientes": "false"},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def api_tarea_general(texto: str, fecha: str | None = None, prioridad: str = "media", tipo: str = "general", nicho: str | None = None):
    nicho_value = None
    if nicho:
        nicho_slug = _resolve_nicho_slug(nicho)
        if nicho_slug:
            nicho_value = nicho_slug
        else:
            fallback = _slugify_nicho(nicho)
            nicho_value = fallback or None
    payload = {
        "texto": texto,
        "prioridad": prioridad,
        "tipo": tipo,
        "nicho": nicho_value,
        "fecha": fecha,
    }
    if fecha:
        try:
            datetime.fromisoformat(fecha)
        except ValueError:
            return {"error": "fecha_invalida"}
    r = http_client.post("/tareas", json={k: v for k, v in payload.items() if v is not None}, headers=_auth_headers())
    return r.json() if r.status_code in (200, 201) else {"error": r.text, "status": r.status_code}


def crear_tarea_lead(dominio: str, texto: str, fecha: str = None, prioridad: str = "media"):
    payload = {"dominio": dominio, "texto": texto, "prioridad": prioridad, "tipo": "lead", "fecha": fecha}
    if fecha:
        try:
            datetime.fromisoformat(fecha)
        except ValueError:
            return {"error": "fecha_invalida"}
    st.session_state["lead_actual"] = dominio
    r = http_client.post("/tareas", json={k: v for k, v in payload.items() if v is not None}, headers=_auth_headers())
    return r.json() if r.status_code in (200, 201) else {"error": r.text, "status": r.status_code}


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
        data = r.json()
        if isinstance(data, list):
            return {"nichos": data}
        return data
    return {"error": r.text, "status": r.status_code}


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


def api_leads_por_nicho(nicho: str):
    slug = _resolve_nicho_slug(nicho) or _slugify_nicho(nicho)
    slug = slug or nicho
    r = http_client.get(f"/leads_por_nicho?nicho={slug}", headers=_auth_headers())
    return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


def mover_lead(dominio: str, origen: str, destino: str):
    st.session_state["lead_actual"] = dominio
    try:
        origen_slug = _resolve_nicho_slug(origen) or _slugify_nicho(origen) or origen
        destino_slug = _resolve_nicho_slug(destino) or _slugify_nicho(destino) or destino
        r = http_client.post(
            "/mover_lead",
            headers=_auth_headers(),
            json={"dominio": dominio, "origen": origen_slug, "destino": destino_slug},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def editar_nicho(nicho_actual: str, nuevo_nombre: str):
    try:
        actual_slug = _resolve_nicho_slug(nicho_actual) or _slugify_nicho(nicho_actual) or nicho_actual
        r = http_client.post(
            "/editar_nicho",
            headers=_auth_headers(),
            json={"nicho_actual": actual_slug, "nuevo_nombre": nuevo_nombre},
        )
        if r.status_code == 200:
            return r.json()
        return _handle_resp(r)
    except Exception as e:
        return {"error": str(e)}


def eliminar_nicho(nicho: str, confirm: bool = False):
    """
    Borrado verificado de nicho:
    - confirm=False -> devuelve 'needs_confirmation' + nº de leads.
    - confirm=True  -> hace DELETE y verifica en /mis_nichos que el nicho ya no aparece.
    """
    try:
        slug = _resolve_nicho_slug(nicho) or _slugify_nicho(nicho) or (nicho or "").strip()
        if not slug:
            return {"error": "Nicho no válido."}

        if not confirm:
            leads_count = _count_leads_in_nicho(slug)
            return {
                "needs_confirmation": True,
                "nicho": nicho,
                "nicho_slug": slug,
                "leads": max(leads_count, 0),
                "message": (
                    f"Por favor, confirma que deseas eliminar el nicho \"{nicho}\". "
                    "Una vez eliminado, no podrás recuperarlo."
                ),
            }

        r = http_client.delete("/eliminar_nicho", headers=_auth_headers(), params={"nicho": slug})

        if r.status_code == 404:
            st.session_state.pop("mis_nichos_fresh", None)
            return {"ok": False, "status": 404, "message": "El nicho no existe o ya fue eliminado."}

        if r.status_code != 200:
            return _handle_resp(r)

        fresh = _fetch_mis_nichos_fresh()
        st.session_state["mis_nichos_fresh"] = fresh

        still_there = False
        for n in fresh:
            if (n.get("nicho") or "").strip() == slug:
                still_there = True
                break

        if still_there:
            rest = _count_leads_in_nicho(slug)
            msg = (
                "He enviado la solicitud de eliminación, pero el nicho aún aparece en el listado. "
                "Puede ser una demora de sincronización."
            )
            if isinstance(rest, int) and rest >= 0:
                msg += f" Quedan {rest} leads asociados."
            msg += " Abre la página *Mis Nichos* para confirmar o reintenta en unos segundos."
            return {"ok": False, "status": 200, "message": msg}

        deleted = 0
        try:
            body = r.json() or {}
            deleted = int(body.get("deleted", 0))
        except Exception:
            pass
        return {"ok": True, "deleted": deleted, "nicho": slug}

    except Exception as e:
        return {"error": str(e)}


def eliminar_lead(dominio: str, solo_de_este_nicho: bool = True, nicho: str | None = None):
    st.session_state["lead_actual"] = dominio
    params = {"dominio": dominio, "solo_de_este_nicho": solo_de_este_nicho}
    if nicho:
        nicho_slug = _resolve_nicho_slug(nicho)
        if nicho_slug:
            params["nicho"] = nicho_slug
        else:
            if solo_de_este_nicho:
                return {
                    "error": f"Nicho '{nicho}' no encontrado. Prueba con el nombre exacto o su slug.",
                    "status": 404,
                }
            fallback = _slugify_nicho(nicho)
            if fallback:
                params["nicho"] = fallback
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
        slug = _resolve_nicho_slug(nicho)
        if not slug:
            slug = _slugify_nicho(nicho)
        if slug:
            params["nicho"] = slug
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
    return {"error": r.text, "status": r.status_code}


TOOLS = {
    "buscar_leads": buscar_leads,
    "api_buscar": _tool_api_buscar,
    "api_buscar_variantes_seleccionadas": _tool_api_buscar_variantes_seleccionadas,
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
    # Eliminadas definiciones de extracción/exportación.
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
            "description": "Elimina un nicho completo. Requiere confirmación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nicho": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
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
    nichos = st.session_state.get("mis_nichos_fresh")
    if nichos is None:
        resp_mis_nichos = cached_get("/mis_nichos", token)
        if isinstance(resp_mis_nichos, list):
            nichos = resp_mis_nichos
        elif isinstance(resp_mis_nichos, dict):
            nichos = resp_mis_nichos.get("nichos", [])
        else:
            nichos = []
    tareas = cached_get("tareas_pendientes", token) or []
    resumen_nichos = ", ".join(
        (n.get("nicho_original") or n.get("nicho") or "").strip() for n in nichos
        if (n.get("nicho_original") or n.get("nicho"))
    ) or "ninguno"
    resumen_tareas = f"Tienes {len(tareas)} tareas pendientes."
    return (
        "Eres un asistente conectado a herramientas del **gestor de leads**, pero **no puedes extraer ni exportar leads desde el chat**. "
        "Si el usuario pide extraer/exportar, responde SIEMPRE con el mensaje oficial de extracción (no ejecutes más acciones).\n\n"
        "Capacidades permitidas desde el chat:\n"
        "• Tareas: crear/editar/completar (generales, por nicho y por lead).\n"
        "• Leads: ver/actualizar estado, añadir notas, mover entre nichos, eliminar.\n"
        "• Nichos: listar, renombrar, eliminar (SIEMPRE pide confirmación antes de borrar; no confirmes borrado si la tool no retorna ok=True).\n"
        "  Para eliminar nichos, primero pide confirmación. Tras confirmar, no anuncies éxito a menos que la tool retorne ok=True. "
        "Si la tool indica verificación fallida, informa al usuario sin afirmar el borrado.\n"
        "• Historial y memoria: consultar y guardar memoria.\n\n"
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

    # Cualquier intento de extraer o exportar leads desde el asistente devuelve el mensaje oficial.
    if es_intencion_extraer_leads(pregunta):
        content = _extraccion_msg()
        st.session_state.chat.append({"role": "assistant", "content": content})
        with st.chat_message("assistant"):
            st.markdown(content)
        st.stop()
    else:
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

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")

# QA manual:
# - "haz una extracción de leads" → responde solo con el mensaje “Esta funcionalidad…” sin banners adicionales.
# - "si hay una tarea de lead llamada X, edítala" + "el dominio es midominio.es" → opera usando /tareas?tipo=lead&dominio=...
# - "añade una nota al lead midominio.es: ..." y luego "ver nota de midominio.es" → guarda en /guardar_info_extra y lee desde /info_extra.
# - Tras cada respuesta no se muestran botones rápidos (Ver tareas / Añadir nota / Cambiar estado).

