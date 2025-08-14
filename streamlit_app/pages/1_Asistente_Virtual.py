import os
import json
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, get_openai_client
from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.auth_utils import get_session_user, logout_button
from streamlit_app.utils.http_client import get as http_get, post as http_post, delete as http_delete, health_ok
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


def _require_subscription() -> bool:
    """Muestra CTA si el plan no permite la acción."""
    if tiene_suscripcion_activa(plan):
        return True
    st.warning("Esta acción requiere una suscripción activa.")
    subscription_cta()
    return False


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
    st.session_state["lead_actual"] = dominio
    try:
        r = http_get("/estado_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def actualizar_estado_lead(dominio: str, estado: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_post("/estado_lead", headers=_auth_headers(), json={"dominio": dominio, "estado": estado})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def obtener_nota_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_get("/nota_lead", headers=_auth_headers(), params={"dominio": dominio})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def actualizar_nota_lead(dominio: str, nota: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_post("/nota_lead", headers=_auth_headers(), json={"dominio": dominio, "nota": nota})
        if r.status_code == 200:
            return r.json()
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def obtener_tareas_lead(dominio: str):
    st.session_state["lead_actual"] = dominio
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
        try:
            datetime.fromisoformat(fecha)
            payload["fecha"] = fecha
        except ValueError:
            return {"error": "fecha_invalida"}
    st.session_state["lead_actual"] = dominio
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
    st.session_state["lead_actual"] = dominio
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


# --- Nuevas herramientas conectadas al backend ---

def buscar(cliente_ideal: str, forzar_variantes: bool = False, contexto_extra: str | None = None):
    if not _require_subscription():
        return {"error": "suscripcion_requerida"}
    payload = {"cliente_ideal": cliente_ideal, "forzar_variantes": forzar_variantes}
    if contexto_extra:
        payload["contexto_extra"] = contexto_extra
    try:
        r = http_post("/buscar", headers=_auth_headers(), json=payload)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def buscar_variantes_seleccionadas(variantes: list[str]):
    if not _require_subscription():
        return {"error": "suscripcion_requerida"}
    try:
        r = http_post(
            "/buscar_variantes_seleccionadas",
            headers=_auth_headers(),
            json={"variantes": variantes},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def extraer_multiples(urls: list[str], pais: str = "ES"):
    if not _require_subscription():
        return {"error": "suscripcion_requerida"}
    try:
        r = http_post(
            "/extraer_multiples",
            headers=_auth_headers(),
            json={"urls": urls, "pais": pais},
        )
        if r.status_code == 200:
            datos = r.json()
            st.session_state["export_payload"] = datos.get("payload_export")
            return datos
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def exportar_csv(urls: list[str], nicho: str, pais: str = "ES"):
    if not _require_subscription():
        return {"error": "suscripcion_requerida"}
    if not nicho:
        return {"error": "nicho_requerido"}
    try:
        r = http_post(
            "/exportar_csv",
            headers=_auth_headers(),
            json={"urls": urls, "pais": pais, "nicho": nicho},
        )
        if r.status_code == 200:
            st.session_state["last_csv"] = r.content
            st.session_state["last_csv_name"] = f"{nicho}.csv"
            st.toast("Leads guardados en la base de datos")
            return {"status": "ok"}
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def leads_por_nicho(nicho: str):
    try:
        r = http_get("/leads_por_nicho", headers=_auth_headers(), params={"nicho": nicho})
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def mover_lead(dominio: str, origen: str, destino: str):
    st.session_state["lead_actual"] = dominio
    try:
        r = http_post(
            "/mover_lead",
            headers=_auth_headers(),
            json={"dominio": dominio, "origen": origen, "destino": destino},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def editar_nicho(nicho_actual: str, nuevo_nombre: str):
    try:
        r = http_post(
            "/editar_nicho",
            headers=_auth_headers(),
            json={"nicho_actual": nicho_actual, "nuevo_nombre": nuevo_nombre},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def eliminar_nicho(nicho: str):
    try:
        r = http_delete(
            "/eliminar_nicho",
            headers=_auth_headers(),
            params={"nicho": nicho},
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def eliminar_lead(dominio: str, solo_de_este_nicho: bool = True, nicho: str | None = None):
    st.session_state["lead_actual"] = dominio
    params = {"dominio": dominio, "solo_de_este_nicho": solo_de_este_nicho}
    if nicho:
        params["nicho"] = nicho
    try:
        r = http_delete("/eliminar_lead", headers=_auth_headers(), params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def historial_tareas(tipo: str = "general", nicho: str | None = None):
    params = {"tipo": tipo}
    if nicho:
        params["nicho"] = nicho
    try:
        r = http_get("/historial_tareas", headers=_auth_headers(), params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def tareas_pendientes():
    if not _require_subscription():
        return {"error": "suscripcion_requerida"}
    try:
        r = http_get("/tareas_pendientes", headers=_auth_headers())
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            get_session_user(require_auth=True)
        return {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def _render_lead_actions():
    dominio = st.session_state.get("lead_actual")
    if not dominio:
        return
    c1, c2, c3 = st.columns(3)
    if c1.button("Ver tareas de este lead", key=f"ver_tareas_{dominio}"):
        tareas = obtener_tareas_lead(dominio)
        if tareas.get("error"):
            st.error(tareas["error"])
        else:
            for t in tareas.get("tareas", []):
                st.write(f"- {t.get('texto')} ({t.get('prioridad')})")
                if st.button("Completar", key=f"compl_{t.get('id')}"):
                    res = completar_tarea(t.get("id"))
                    if res.get("error"):
                        st.error(res["error"])
                    else:
                        st.success("Tarea completada")
    if c2.button("Añadir nota", key=f"add_nota_{dominio}"):
        nota = st.text_area("Nota", key=f"nota_{dominio}")
        if st.button("Guardar nota", key=f"guardar_nota_{dominio}"):
            res = actualizar_nota_lead(dominio, nota)
            if res.get("error"):
                st.error(res["error"])
            else:
                st.toast("Nota guardada")
    if c3.button("Cambiar estado", key=f"cambiar_estado_{dominio}"):
        estado = st.selectbox(
            "Nuevo estado",
            ["nuevo", "contactado", "en_proceso", "cliente", "descartado"],
            key=f"estado_{dominio}",
        )
        if st.button("Guardar estado", key=f"guardar_estado_{dominio}"):
            res = actualizar_estado_lead(dominio, estado)
            if res.get("error"):
                st.error(res["error"])
            else:
                st.toast("Estado actualizado")


TOOLS = {
    "buscar_leads": buscar_leads,
    "buscar": buscar,
    "buscar_variantes_seleccionadas": buscar_variantes_seleccionadas,
    "extraer_multiples": extraer_multiples,
    "exportar_csv": exportar_csv,
    "obtener_estado_lead": obtener_estado_lead,
    "actualizar_estado_lead": actualizar_estado_lead,
    "obtener_nota_lead": obtener_nota_lead,
    "actualizar_nota_lead": actualizar_nota_lead,
    "obtener_tareas_lead": obtener_tareas_lead,
    "crear_tarea_lead": crear_tarea_lead,
    "completar_tarea": completar_tarea,
    "historial_lead": historial_lead,
    "mis_nichos": mis_nichos,
    "leads_por_nicho": leads_por_nicho,
    "mover_lead": mover_lead,
    "editar_nicho": editar_nicho,
    "eliminar_nicho": eliminar_nicho,
    "eliminar_lead": eliminar_lead,
    "historial_tareas": historial_tareas,
    "tareas_pendientes": tareas_pendientes,
    "obtener_memoria": obtener_memoria,
    "guardar_memoria": guardar_memoria,
}


tool_defs = [
    {
        "type": "function",
        "function": {
            "name": "buscar",
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
            "name": "buscar_variantes_seleccionadas",
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
            "name": "extraer_multiples",
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
            "name": "exportar_csv",
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
            "name": "leads_por_nicho",
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
            "name": "tareas_pendientes",
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
            while msg.tool_calls:
                st.session_state.chat.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
                for tc in msg.tool_calls:
                    func = TOOLS.get(tc.function.name)
                    args = json.loads(tc.function.arguments or "{}")
                    resultado = func(**args) if func else {"error": f"Tool {tc.function.name} no disponible"}
                    st.session_state.chat.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(resultado, ensure_ascii=False)})
                messages = [{"role": "system", "content": contexto}] + st.session_state.chat
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
        _render_lead_actions()
        if st.session_state.get("last_csv"):
            st.download_button(
                "Descargar CSV",
                st.session_state.get("last_csv"),
                file_name=st.session_state.get("last_csv_name", "leads.csv"),
                mime="text/csv",
            )

