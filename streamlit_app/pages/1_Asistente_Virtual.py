import os
import json
import streamlit as st
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, get_openai_client
from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.auth_utils import get_session_user, logout_button
from streamlit_app.utils.http_client import get as http_get, post as http_post, health_ok
from streamlit_app.cookies_utils import init_cookie_manager_mount

init_cookie_manager_mount()

st.set_page_config(page_title="Asistente Virtual", page_icon="🤖")


token, user = get_session_user(require_auth=True)

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

st.title("🤖 Tu Asistente Virtual")
st.write(
    "Desde este asistente puedes **extraer leads**, **crear tareas**, **gestionar nichos** y consultar información. "
    "Usa el chat para pedir acciones concretas (p. ej., “busca dentistas en Madrid y crea un nicho”)."
)
st.divider()

plan = (user or {}).get("plan", "free")


def _auth_headers():
    """Authorization headers using the token in session."""
    return {"Authorization": f"Bearer {st.session_state.token}"}


# ────────────────── Funciones de herramientas ─────────────────────
def buscar_leads(query: str):
    try:
        r = http_get("/buscar_leads", headers=_auth_headers(), params={"query": query})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        if not health_ok():
            st.info("Conectando con el backend...")
        return {"error": str(e)}


def obtener_estado_lead(dominio: str):
    try:
        r = http_get("/estado_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def actualizar_estado_lead(dominio: str, estado: str):
    try:
        r = http_post("/estado_lead", headers=_auth_headers(), json={"dominio": dominio, "estado": estado})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def obtener_nota_lead(dominio: str):
    try:
        r = http_get("/nota_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def actualizar_nota_lead(dominio: str, nota: str):
    try:
        r = http_post("/nota_lead", headers=_auth_headers(), json={"dominio": dominio, "nota": nota})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def obtener_tareas_lead(dominio: str):
    try:
        r = http_get("/tareas_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def crear_tarea_lead(dominio: str, texto: str, fecha: str = None, prioridad: str = "media"):
    payload = {"texto": texto, "dominio": dominio, "tipo": "lead", "prioridad": prioridad}
    if fecha:
        payload["fecha"] = fecha
    try:
        r = http_post("/tarea_lead", headers=_auth_headers(), json=payload)
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def completar_tarea(tarea_id: int):
    try:
        r = http_post("/tarea_completada", headers=_auth_headers(), params={"tarea_id": tarea_id})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def historial_lead(dominio: str):
    try:
        r = http_get("/historial_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def mis_nichos():
    try:
        r = http_get("/mis_nichos", headers=_auth_headers())
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def obtener_memoria():
    try:
        r = http_get("/mi_memoria", headers=_auth_headers())
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def guardar_memoria(descripcion: str):
    try:
        r = http_post("/mi_memoria", headers=_auth_headers(), json={"descripcion": descripcion})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


TOOLS = {
    "buscar_leads": buscar_leads,
    "obtener_estado_lead": obtener_estado_lead,
    "actualizar_estado_lead": actualizar_estado_lead,
    "obtener_nota_lead": obtener_nota_lead,
    "actualizar_nota_lead": actualizar_nota_lead,
    "obtener_tareas_lead": obtener_tareas_lead,
    "crear_tarea_lead": crear_tarea_lead,
    "completar_tarea": completar_tarea,
    "historial_lead": historial_lead,
    "mis_nichos": mis_nichos,
    "obtener_memoria": obtener_memoria,
    "guardar_memoria": guardar_memoria,
}


tool_defs = [
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
            "name": "mis_nichos",
            "description": "Devuelve los nichos del usuario",
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
    nichos = cached_get("mis_nichos", st.session_state.token).get("nichos", [])
    tareas = cached_get("tareas_pendientes", st.session_state.token).get("tareas", [])
    resumen_nichos = ", ".join(n["nicho_original"] for n in nichos) or "ninguno"
    resumen_tareas = f"Tienes {len(tareas)} tareas pendientes."
    return (
        "Eres un asistente virtual conectado a la base de datos del usuario. "
        "Puedes buscar leads, cambiar estados, añadir notas y tareas, y consultar historial. "
        "Responde de forma clara y breve, proponiendo acciones útiles.\n\n"
        f"Nichos del usuario: {resumen_nichos}.\n{resumen_tareas}"
    )


# ────────────────── Conversación ────────────────────
MAX_TURNS = 20
if "chat" not in st.session_state:
    st.session_state.chat = []
elif len(st.session_state.chat) > MAX_TURNS * 2:
    st.session_state.chat = st.session_state.chat[-MAX_TURNS * 2:]

for entrada in st.session_state.chat:
    if entrada["role"] in ("user", "assistant"):
        with st.chat_message(entrada["role"]):
            st.markdown(entrada["content"])

pregunta = st.chat_input("Haz una pregunta sobre tus nichos, leads o tareas...")

if pregunta:
    if not tiene_suscripcion_activa(plan):
        st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
        subscription_cta()
    else:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        contexto = build_system_prompt()
        messages = [{"role": "system", "content": contexto}] + st.session_state.chat

        with st.spinner("Pensando..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tool_defs,
                )
                msg = response.choices[0].message
            except Exception:
                st.warning("El servidor de IA está ocupado. Inténtalo de nuevo en unos segundos.")
                st.stop()

            if msg.tool_calls:
                st.session_state.chat.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
                for tc in msg.tool_calls:
                    func = TOOLS.get(tc.function.name)
                    args = json.loads(tc.function.arguments or "{}")
                    resultado = func(**args) if func else {"error": f"Tool {tc.function.name} no disponible"}
                    st.session_state.chat.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(resultado, ensure_ascii=False)})
                messages = [{"role": "system", "content": contexto}] + st.session_state.chat
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                    )
                    msg = response.choices[0].message
                except Exception:
                    st.warning("El servidor de IA está ocupado. Inténtalo de nuevo en unos segundos.")
                    st.stop()

        content = msg.content or ""
        st.session_state.chat.append({"role": "assistant", "content": content})
        with st.chat_message("assistant"):
            st.markdown(content)
            c1, c2, c3 = st.columns(3)
            c1.button("Ver tareas de este lead", key=f"ver_tareas_{len(st.session_state.chat)}")
            c2.button("Añadir nota", key=f"add_nota_{len(st.session_state.chat)}")
            c3.button("Cambiar estado", key=f"cambiar_estado_{len(st.session_state.chat)}")

