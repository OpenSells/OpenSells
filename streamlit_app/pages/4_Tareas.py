import os
import requests
import streamlit as st
from hashlib import md5
from urllib.parse import urlparse
import time
from datetime import date
from typing import Any, Dict, Iterable, List
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.plan_utils import resolve_user_plan, tiene_suscripcion_activa, subscription_cta
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.auth_session import is_authenticated, remember_current_page, get_auth_token
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.utils.leads_api import (
    api_info_extra,
    api_nota_lead,
    api_estado_lead,
    api_eliminar_lead,
)
# ────────────────── Config ──────────────────────────
load_dotenv()


def _resolve_backend_url() -> str:
    """Resolve backend base URL preferring env vars, then secrets, then localhost."""
    env_value = os.getenv("BACKEND_URL")
    if env_value:
        return env_value
    try:
        secret_value = st.secrets.get("BACKEND_URL")
    except Exception:
        secret_value = None
    return secret_value or "http://127.0.0.1:8000"


BACKEND_URL = _resolve_backend_url()

st.set_page_config(page_title="Tareas", page_icon="📋", layout="centered")

PAGE_NAME = "Tareas"
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

debug = st.sidebar.checkbox("Debug tareas", value=False)

plan = resolve_user_plan(token)["plan"]

HDR = {"Authorization": f"Bearer {token}"}
ICON = {"general": "🧠", "nicho": "📂", "lead": "🌐"}
P_ICON = {"alta": "🔴 Alta", "media": "🟡 Media", "baja": "🟢 Baja"}
HOY = date.today()

PRIO_ORDER = {"alta": 0, "media": 1, "baja": 2}

st.caption(f"DEBUG BACKEND_URL = {BACKEND_URL}")


def crear_tarea_backend(payload: Dict[str, Any], headers: Dict[str, str], debug_flag: bool) -> bool:
    """Envía el payload al backend y muestra mensajes de depuración si procede."""
    url = f"{BACKEND_URL.rstrip('/')}/tareas"
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except Exception as exc:
        st.error("No se pudo conectar con el backend al crear la tarea.")
        if debug_flag:
            st.caption(f"DEBUG POST /tareas → error: {exc}")
        return False

    snippet = (response.text or "").replace("\n", "\\n")[:200]
    if debug_flag:
        st.caption(f"DEBUG POST /tareas → {response.status_code} {snippet}")

    if response.status_code not in (200, 201):
        detail = None
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("message") or data
        if detail is None:
            detail = snippet or "Respuesta no válida del backend."
        if isinstance(detail, dict):
            detail = detail.get("detail") or str(detail)
        st.error(f"No se pudo crear la tarea ({response.status_code}): {detail}")
        return False

    limpiar_cache()
    return True

# Redirección automática desde enlace
params = st.query_params

if "lead" in params:
    st.session_state["lead_seleccionado"] = params["lead"]
    st.session_state["tareas_tipo_ui"] = "Leads"
    st.query_params.clear()
elif "nicho" in params:
    st.session_state["nicho_seleccionado"] = params["nicho"]
    st.session_state["tareas_tipo_ui"] = "Nichos"
    st.query_params.clear()

if "tareas_tipo_ui" not in st.session_state:
    st.session_state["tareas_tipo_ui"] = "Pendientes"

# ────────────────── Helpers ─────────────────────────
def _hash(v):
    return md5(str(v).encode()).hexdigest()

def norm_dom(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return urlparse(url).netloc.replace("www.", "").split("/")[0]


def ensure_list(payload: Any) -> List[Dict[str, Any]]:
    """
    Normaliza la respuesta del backend a una lista de tareas.
    Acepta: lista directa, dict con 'items'/'tareas'/'results'/'data',
    o dict id->objeto (devuelve sus values).
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "tareas", "results", "data"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
        values = list(payload.values())
        if values and all(isinstance(v, dict) for v in values):
            return values
        return [payload]
    return []


def sort_tareas(iterable: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Orden: prioridad (alta>media>baja), luego fecha asc (YYYY-MM-DD), luego timestamp asc si existe.
    """
    tareas = list(iterable)

    def _key(t: Dict[str, Any]):
        prio = PRIO_ORDER.get((t.get("prioridad") or "").lower(), 99)
        fecha = t.get("fecha") or "9999-12-31"
        ts = t.get("timestamp") or ""
        return (prio, fecha, ts)

    return sorted(tareas, key=_key)


# ────────────────── Datos base ──────────────────────
datos_nichos = cached_get("/mis_nichos", token)
if isinstance(datos_nichos, list):
    lista_nichos = datos_nichos
elif isinstance(datos_nichos, dict):
    lista_nichos = datos_nichos.get("nichos", [])
else:
    lista_nichos = []
map_n = {n.get("nicho"): n.get("nicho_original") for n in lista_nichos if n.get("nicho")}

@st.cache_data(ttl=30)
def fetch_tareas_pendientes(tipo: str):
    params = {"solo_pendientes": True}
    if tipo in ("general", "nicho", "lead"):
        params["tipo"] = tipo
    resp = http_client.get(
        "/tareas_pendientes",
        headers=HDR,
        params=params,
    )
    if resp.status_code == 200:
        return resp.json()
    return []

# ────────────────── Render tabla ────────────────────
def render_list(items, prefix: str):
    items = sort_tareas(ensure_list(items))

    if not items:
        st.info("No hay tareas para mostrar.")
        return

    for i, t in enumerate(items):
        unique_key = f"{prefix}_{t['id']}_{i}"
        cols = st.columns([1, 3, 2, 1.5, 1.5, 0.8, 0.8])

        tipo = ICON.get(t.get("tipo"), "❔")
        texto = t['texto']
        raw_fecha = t.get("fecha")
        if raw_fecha and raw_fecha != "Sin fecha":
            try:
                dt = date.fromisoformat(raw_fecha)
                fecha = dt.strftime("%d/%m/%y")
            except:
                fecha = raw_fecha
                dt = None
        else:
            fecha = "Sin fecha"
            dt = None

        tipo_tarea = t.get("tipo", "general")

        if tipo_tarea == "nicho":
            asignado = f"📂 {map_n.get(t.get('nicho'), t.get('nicho')) or '—'}"
        elif tipo_tarea == "lead":
            asignado = f"🌐 {t.get('dominio') or '—'}"
        else:
            asignado = "🧠 General"

        prioridad_raw = t.get("prioridad", "media")
        prioridad = P_ICON.get(prioridad_raw if prioridad_raw in P_ICON else "media")

        cols[0].markdown(f"{tipo}")
        if t.get("auto", False):
            cols[1].markdown(f"**{texto}** _(Auto)_")
        else:
            cols[1].markdown(f"**{texto}**")
        cols[2].markdown(asignado)  # Enlace solo si es lead o nicho (Markdown puro)
        cols[3].markdown(fecha)
        cols[4].markdown(prioridad)

        if cols[5].button("✔️", key=f"done_{unique_key}"):
            if not tiene_suscripcion_activa(plan):
                st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                subscription_cta()
            else:
                cached_post("tarea_completada", token, params={"tarea_id": t['id']})
                limpiar_cache()  # ✅ Añadir esto
                st.success(f"Tarea {t['id']} marcada como completada ✅")
                st.rerun()

        if f"editando_{unique_key}" not in st.session_state:
            st.session_state[f"editando_{unique_key}"] = False

        if cols[6].button("📝", key=f"edit_{unique_key}"):
            st.session_state[f"editando_{unique_key}"] = not st.session_state[f"editando_{unique_key}"]

        if st.session_state[f"editando_{unique_key}"]:
            st.markdown("#### ✏️ Editar tarea")
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1.5, 1.5])
            nuevo_texto = c1.text_input("Tarea", value=t.get("texto", ""), key=f"texto_{unique_key}")
            nueva_fecha = c2.date_input("Fecha", value=dt if dt else HOY, key=f"fecha_{unique_key}")
            prioridad_actual = t.get("prioridad", "media")
            if prioridad_actual not in ["alta", "media", "baja"]:
                prioridad_actual = "media"

            nueva_prioridad = c3.selectbox(
                "Prioridad",
                ["alta", "media", "baja"],
                index=["alta", "media", "baja"].index(prioridad_actual),
                key=f"prio_{unique_key}"
            )

            if c4.button("💾", key=f"guardar_edit_{unique_key}"):
                if not tiene_suscripcion_activa(plan):
                    st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                    subscription_cta()
                else:
                    cached_post(
                        "editar_tarea",
                        token,
                        payload={
                            "texto": nuevo_texto.strip(),
                            "fecha": nueva_fecha.strftime("%Y-%m-%d") if nueva_fecha else None,
                            "prioridad": nueva_prioridad,
                            "tipo": t.get("tipo"),
                            "nicho": t.get("nicho"),
                            "dominio": t.get("dominio"),
                            "auto": t.get("auto", False),
                        },
                        params={"tarea_id": t["id"]}
                    )
                    st.session_state[f"editando_{unique_key}"] = False
                    limpiar_cache()  # ✅ IMPORTANTE: limpia caché antes de recargar
                    st.success("Tarea actualizada ✅")
                    st.rerun()

            if c5.button("❌", key=f"cerrar_edit_{unique_key}"):
                st.session_state[f"editando_{unique_key}"] = False
                st.rerun()

# ────────────────── Layout ──────────────────────────

st.title("📋 Tareas activas")
opciones_ui = ["Pendientes", "General", "Nichos", "Leads"]
seleccion = st.radio(
    "Vista",
    options=opciones_ui,
    key="tareas_tipo_ui",
    label_visibility="collapsed",
    horizontal=True,
)
label_to_tipo = {"Pendientes": "todas", "General": "general", "Nichos": "nicho", "Leads": "lead"}
todos = fetch_tareas_pendientes(label_to_tipo[seleccion])
if debug:
    st.caption(f"debug: {label_to_tipo[seleccion]}={len(ensure_list(todos))}")

if seleccion == "Pendientes":
    st.subheader("Pendientes")
    render_list(todos, "all")

# Generales
elif seleccion == "General":
    st.subheader("🧠 Tareas generales")

    # Toggle para añadir tarea
    if st.toggle("➕ Añadir tarea general", key="toggle_tarea_general"):
        with st.form(key="form_general"):
            texto = st.text_input("📝 Descripción", key="t_gen")
            cols = st.columns(2)
            fecha = cols[0].date_input("📅 Fecha", value=None, key="f_gen")
            prioridad = cols[1].selectbox("🔥 Prioridad", ["alta", "media", "baja"], key="p_gen", index=1)

            if st.form_submit_button("💾 Crear tarea"):
                if texto.strip():
                    if not tiene_suscripcion_activa(plan):
                        st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                        subscription_cta()
                    else:
                        payload = {
                            "texto": texto.strip(),
                            "tipo": "general",
                            "prioridad": prioridad,
                        }
                        if fecha:
                            payload["fecha"] = fecha.strftime("%Y-%m-%d")
                        if crear_tarea_backend(payload, HDR, debug):
                            st.success("Tarea creada correctamente.")
                            st.rerun()
                else:
                    st.warning("La descripción es obligatoria.")

    # Tareas activas
    gen = todos
    st.markdown("#### 📋 Tareas activas")
    render_list(gen, "g")

    # Toggle para historial
    if st.toggle("📜 Ver historial de tareas generales", key="toggle_historial_general"):
        datos_hist = cached_get(
            "historial_tareas",
            token,
            query={"tipo": "general"},
            nocache_key=time.time()
        )
        historial = datos_hist.get("historial", []) if datos_hist else []
        completadas = [
            h for h in historial
            if h.get("tipo") == "general" and h.get("descripcion", "").lower().startswith("tarea completada")
        ]
        if completadas:
            for h in completadas:
                st.markdown(f"✅ **{h['descripcion']}**")
                st.caption(h["timestamp"])
        else:
            st.info("No hay tareas completadas.")

# Nichos
elif seleccion == "Nichos":
    if "nicho_seleccionado" not in st.session_state:
        st.session_state["nicho_seleccionado"] = None

    ln_data = cached_get("/mis_nichos", token)
    if isinstance(ln_data, list):
        ln = ln_data
    elif isinstance(ln_data, dict):
        ln = ln_data.get("nichos", [])
    else:
        ln = []

    if not ln:
        st.info("Crea nichos para ver tareas.")
    else:
        # Fase 1: Lista de nichos
        if not st.session_state["nicho_seleccionado"]:
            st.subheader("📂 Nichos")

            filtro_nicho = st.text_input("Buscar por nombre de nicho", placeholder="Ej: restaurantes")
            filtrados = [
                n
                for n in ln
                if filtro_nicho.lower()
                in (n.get("nicho_original") or n.get("nicho") or "").lower()
            ] if filtro_nicho else ln

            if not filtrados:
                st.info("No se encontraron nichos con ese nombre.")
            else:
                for n in filtrados:
                    nombre = (n.get("nicho_original") or n.get("nicho") or "").strip()
                    cols = st.columns([6, 1])
                    cols[0].markdown(f"📁 **{nombre}**")
                    if cols[1].button("➡️ Ver", key=f"ver_nicho_{nombre}"):
                        st.session_state["nicho_seleccionado"] = nombre
                        st.rerun()

        # Fase 2: Vista del nicho seleccionado
        else:
            elegido = st.session_state["nicho_seleccionado"]
            nk = next((n for n in ln if n["nicho_original"] == elegido), None)
            if nk is None:
                st.error("❌ El nicho seleccionado ya no existe o fue filtrado.")
                st.session_state["nicho_seleccionado"] = None
                st.rerun()

            cols = st.columns([6, 1])
            cols[0].markdown(f"### 📁 {elegido}")
            if cols[1].button("⬅️ Volver", key="volver_nichos", use_container_width=True):
                st.session_state["nicho_seleccionado"] = None
                st.rerun()

            # Toggle para añadir tarea
            if st.toggle("➕ Añadir tarea al nicho actual", key="toggle_tarea_nicho"):
                with st.form(key="form_nicho"):
                    texto = st.text_input("📝 Descripción", key="t_nicho")
                    cols_f = st.columns(2)
                    fecha = cols_f[0].date_input("📅 Fecha", value=None, key="f_nicho")
                    prioridad = cols_f[1].selectbox("🔥 Prioridad", ["alta", "media", "baja"], key="p_nicho", index=1)
                    if st.form_submit_button("💾 Crear tarea"):
                        if texto.strip():
                            if not tiene_suscripcion_activa(plan):
                                st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                                subscription_cta()
                            else:
                                payload = {
                                    "texto": texto.strip(),
                                    "tipo": "nicho",
                                    "nicho": nk["nicho"],
                                    "prioridad": prioridad,
                                }
                                if fecha:
                                    payload["fecha"] = fecha.strftime("%Y-%m-%d")
                                if crear_tarea_backend(payload, HDR, debug):
                                    st.success("Tarea creada correctamente.")
                                    st.rerun()
                        else:
                            st.warning("La descripción es obligatoria.")

            tareas_n = [t for t in ensure_list(todos) if t.get("nicho") == nk["nicho"]]
            st.markdown("#### 📋 Tareas activas")
            if debug:
                st.caption(f"debug: nicho={len(tareas_n)}")
            render_list(tareas_n, f"n{nk['nicho']}")

            # Toggle historial
            if st.toggle("📜 Ver historial de tareas de este nicho", key="toggle_historial_nicho"):
                hist_n = cached_get(
                    "historial_tareas",
                    token,
                    query={"tipo": "nicho", "nicho": nk["nicho"]},
                    nocache_key=time.time()  # 👈 fuerza recarga de caché
                )
                historial = hist_n.get("historial", []) if hist_n else []
                completadas = [
                    h for h in historial
                    if h.get("descripcion", "").lower().startswith("tarea completada")
                ]
                if completadas:
                    for h in completadas:
                        st.markdown(f"✅ **{h['descripcion']}**")
                        st.caption(h["timestamp"])
                else:
                    st.info("No hay tareas completadas para este nicho.")

# Leads
elif seleccion == "Leads":

    if "lead_seleccionado" not in st.session_state:
        st.session_state["lead_seleccionado"] = None

    # Modo búsqueda
    if not st.session_state["lead_seleccionado"]:
        q = st.text_input("Filtrar leads por dominio:", placeholder="Ej. clinicadental.com")
        st.session_state["q_lead"] = q

        query = {"query": q} if q else None
        # nocache_key asegura que cada búsqueda se envíe con el token vigente
        datos_buscar = (
            cached_get(
                "buscar_leads",
                token,
                query=query,
                nocache_key=time.time(),
            )
            if query
            else None
        )
        resultados = datos_buscar.get("resultados", []) if datos_buscar else []

        if resultados:
            st.markdown(f"**Total encontrados: {len(resultados)}**")
            for dom in resultados:
                norm = norm_dom(dom)
                cols = st.columns([5, 1])
                cols[0].markdown(f"🌐 [{norm}](https://{norm})", unsafe_allow_html=True)
                if cols[1].button("➡️ Ver", key=f"ver_{norm}"):
                    st.session_state["lead_seleccionado"] = norm
                    st.rerun()
        else:
            st.info("Escribe un dominio para buscar.")
    
    # Modo detalle de lead
    else:
        norm = st.session_state["lead_seleccionado"]
        cols = st.columns([6, 1])
        cols[0].markdown(f"### 🌍 [{norm}](https://{norm})", unsafe_allow_html=True)
        if cols[1].button("⬅️ Volver", key="volver_leads", use_container_width=True):
            st.session_state["lead_seleccionado"] = None
            st.rerun()

        # Toggle añadir tarea
        if st.toggle("➕ Añadir tarea", key="toggle_tarea"):
            with st.form(key="form_tarea_detalle"):
                texto = st.text_input("📝 Descripción", key="tarea_texto_detalle")
                cols_f = st.columns(2)
                fecha = cols_f[0].date_input("📅 Fecha", value=None, key="fecha_detalle")
                prioridad = cols_f[1].selectbox("🔥 Prioridad", ["alta", "media", "baja"], key="prio_detalle", index=1)
                if st.form_submit_button("💾 Crear tarea"):
                    if texto.strip():
                        if not tiene_suscripcion_activa(plan):
                            st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                            subscription_cta()
                        else:
                            payload = {
                                "texto": texto.strip(),
                                "tipo": "lead",
                                "dominio": norm,
                                "prioridad": prioridad,
                            }
                            if fecha:
                                payload["fecha"] = fecha.strftime("%Y-%m-%d")
                            if crear_tarea_backend(payload, HDR, debug):
                                st.success("Tarea creada correctamente.")
                                st.rerun()
                    else:
                        st.warning("La descripción es obligatoria.")

        # Toggle info extra
        if st.toggle("📝 Información extra del lead", key="toggle_info"):
            info_extra = api_info_extra(norm)
            if not info_extra:
                st.info("No hay información adicional para este lead.")
            else:
                estado_actual = info_extra.get("estado_contacto") or "pendiente"
                pendientes = info_extra.get("tareas_pendientes", 0)
                totales = info_extra.get("tareas_totales", 0)

                col_estado, col_tareas = st.columns(2)
                col_estado.metric("Estado actual", estado_actual)
                col_tareas.metric("Tareas pendientes", pendientes)
                col_tareas.metric("Tareas totales", totales)

                estados_validos = ["pendiente", "contactado", "no_responde", "descartado"]
                try:
                    idx_estado = estados_validos.index(estado_actual)
                except ValueError:
                    idx_estado = 0

                with st.form(key="form_estado_lead_detalle"):
                    nuevo_estado = st.selectbox(
                        "Actualizar estado",
                        estados_validos,
                        index=idx_estado,
                        key="estado_detalle",
                    )
                    if st.form_submit_button("Guardar estado"):
                        api_estado_lead(norm, nuevo_estado)

                st.markdown("#### Notas")
                notas = info_extra.get("notas", [])
                if notas:
                    for nota in notas:
                        timestamp = nota.get("timestamp") or ""
                        st.markdown(f"- {nota.get('texto')}")
                        if timestamp:
                            st.caption(timestamp)
                else:
                    st.write("Sin notas guardadas.")

                with st.form(key="form_nota_lead_detalle"):
                    texto_nota = st.text_area("Añadir nota", key="nota_detalle")
                    if st.form_submit_button("Guardar nota"):
                        if texto_nota.strip():
                            api_nota_lead(norm, texto_nota)
                        else:
                            st.warning("Escribe una nota antes de guardar.")

                confirmar_key = "confirmar_delete_lead"
                if st.session_state.get(confirmar_key):
                    st.warning("Confirma la eliminación del lead seleccionado.")
                    col_del_ok, col_del_cancel = st.columns(2)
                    if col_del_ok.button("Sí, eliminar", key="delete_lead_ok"):
                        api_eliminar_lead(norm, True)
                        st.session_state.pop(confirmar_key, None)
                    if col_del_cancel.button("Cancelar", key="delete_lead_cancel"):
                        st.session_state.pop(confirmar_key, None)
                else:
                    if st.button("Eliminar lead", key="delete_lead"):
                        st.session_state[confirmar_key] = True

        st.markdown("#### 📋 Tareas activas")
        tareas_datos = cached_get(
            "tareas_lead",
            token,
            query={"dominio": norm},
            nocache_key=time.time()
        )
        tareas_l = ensure_list(tareas_datos)
        if debug:
            st.caption(f"debug: lead={len(tareas_l)}")
        render_list(
            [t for t in tareas_l if not t.get("completado", False)],
            f"lead_t_{norm}"
        )

        st.markdown("#### 📜 Historial")
        hist_datos = cached_get(
            "historial_lead",
            token,
            query={"dominio": norm},
            nocache_key=time.time()
        )
        historial = hist_datos.get("historial", []) if hist_datos else []
        completadas = [
            h for h in historial
            if h["tipo"] == "tarea" and h["descripcion"].lower().startswith("tarea completada")
        ]
        if completadas:
            for h in completadas:
                st.markdown(f"✅ **{h['descripcion']}**")
                st.caption(h["timestamp"])
        else:
            st.info("No hay tareas completadas para este lead.")