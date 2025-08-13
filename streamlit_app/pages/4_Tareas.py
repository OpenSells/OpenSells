import os
import streamlit as st
from hashlib import md5
from urllib.parse import urlparse
import time
from datetime import date
from dotenv import load_dotenv

from streamlit_app.cache_utils import cached_get, cached_post, limpiar_cache
from streamlit_app.plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from streamlit_app.auth_utils import ensure_token_and_user, logout_button
from streamlit_app.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()
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

st.set_page_config(page_title="Tareas", page_icon="📋", layout="centered")


def api_me(token: str):
    return http_client.get("/me", headers={"Authorization": f"Bearer {token}"})


user, token = ensure_token_and_user(api_me)
if user is None or token is None:
    st.error("No se pudo validar la sesión. Inicia sesión de nuevo.")
    st.stop()

logout_button()

plan = obtener_plan(st.session_state.token)

# Validar el token llamando a un endpoint protegido. Si falla, forzamos logout
validacion = cached_get("protegido", st.session_state.token, nocache_key=time.time())
if not validacion or "detail" in validacion:
    st.error("Token inválido o expirado. Inicia sesión nuevamente.")
    st.stop()

HDR = {"Authorization": f"Bearer {st.session_state.token}"}
ICON = {"general": "🧠", "nicho": "📂", "lead": "🌐"}
P_ICON = {"alta": "🔴 Alta", "media": "🟡 Media", "baja": "🟢 Baja"}
HOY = date.today()

# Redirección automática desde enlace
params = st.query_params

if "lead" in params:
    st.session_state["lead_seleccionado"] = params["lead"]
    st.session_state["tarea_seccion_activa"] = "🌐 Leads"
    st.query_params.clear()

elif "nicho" in params:
    st.session_state["nicho_seleccionado"] = params["nicho"]
    st.session_state["tarea_seccion_activa"] = "📂 Nichos"
    st.query_params.clear()

if "tarea_seccion_activa" not in st.session_state:
    st.session_state["tarea_seccion_activa"] = "⏳ Pendientes"

# ────────────────── Helpers ─────────────────────────
def _hash(v):
    return md5(str(v).encode()).hexdigest()

def norm_dom(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return urlparse(url).netloc.replace("www.", "").split("/")[0]


# ────────────────── Datos base ──────────────────────
datos_tareas = cached_get("tareas_pendientes", st.session_state.token, nocache_key=time.time())
todos = [t for t in (datos_tareas.get("tareas") if datos_tareas else []) if not t.get("completado", False)]
datos_nichos = cached_get("mis_nichos", st.session_state.token)
map_n = {n["nicho"]: n["nicho_original"] for n in (datos_nichos.get("nichos") if datos_nichos else [])}

# ────────────────── Render tabla ────────────────────
def render_list(items: list[dict], key_pref: str):
    items.sort(key=lambda t: t.get("fecha") or "9999-12-31")
    if not items:
        st.info("Sin tareas.")
        return

    for i, t in enumerate(items):
        unique_key = f"{key_pref}_{t['id']}_{i}"
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
        cols[1].markdown(f"**{texto}**")
        cols[2].markdown(asignado)  # Enlace solo si es lead o nicho (Markdown puro)
        cols[3].markdown(fecha)
        cols[4].markdown(prioridad)

        if cols[5].button("✔️", key=f"done_{unique_key}"):
            if not tiene_suscripcion_activa(plan):
                st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                subscription_cta()
            else:
                cached_post("tarea_completada", st.session_state.token, params={"tarea_id": t['id']})
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
                        st.session_state.token,
                        payload={
                            "texto": nuevo_texto.strip(),
                            "fecha": nueva_fecha.strftime("%Y-%m-%d") if nueva_fecha else None,
                            "prioridad": nueva_prioridad,
                            "tipo": t.get("tipo"),
                            "nicho": t.get("nicho"),
                            "dominio": t.get("dominio")
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

st.title("📋 Tareas")
titles = ["⏳ Pendientes", "🧠 General", "📂 Nichos", "🌐 Leads"]

seccion = st.radio(
    "Secciones",
    titles,
    key="tarea_seccion_activa",
    index=titles.index(st.session_state["tarea_seccion_activa"]),
    label_visibility="collapsed",
    horizontal=True,
)

if seccion == titles[0]:
    st.subheader("⏳ Todas las pendientes")
    render_list(todos, "all")

# Generales
elif seccion == titles[1]:
    st.subheader("🧠 Tareas generales")

    # Toggle para añadir tarea
    if st.toggle("➕ Añadir tarea general", key="toggle_tarea_general"):
        with st.form(key="form_general"):
            texto = st.text_input("📝 Descripción", key="t_gen")
            cols = st.columns(2)
            fecha = cols[0].date_input("📅 Fecha", value=None, key="f_gen")
            prioridad = cols[1].selectbox("🔥 Prioridad", ["alta", "media", "baja"], key="p_gen")

            if st.form_submit_button("💾 Crear tarea"):
                if texto.strip():
                    if not tiene_suscripcion_activa(plan):
                        st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                        subscription_cta()
                    else:
                        cached_post(
                            "tarea_lead",
                            st.session_state.token,
                            payload={
                                "texto": texto.strip(),
                                "tipo": "general",
                                "fecha": fecha.strftime("%Y-%m-%d") if fecha else None,
                                "prioridad": prioridad
                            }
                        )
                        limpiar_cache()  # ✅ Limpia la caché para que se vea la nueva tarea
                        st.success("Tarea creada ✅")
                        st.rerun()
                else:
                    st.warning("La descripción es obligatoria.")

    # Tareas activas
    gen = [t for t in todos if t.get("tipo") == "general" and not t.get("completado", False)]
    st.markdown("#### 📋 Tareas activas")
    render_list(gen, "g")

    # Toggle para historial
    if st.toggle("📜 Ver historial de tareas generales", key="toggle_historial_general"):
        datos_hist = cached_get(
            "historial_tareas",
            st.session_state.token,
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
elif seccion == titles[2]:
    if "nicho_seleccionado" not in st.session_state:
        st.session_state["nicho_seleccionado"] = None

    ln_data = cached_get("mis_nichos", st.session_state.token)
    ln = ln_data.get("nichos", []) if ln_data else []

    if not ln:
        st.info("Crea nichos para ver tareas.")
    else:
        # Fase 1: Lista de nichos
        if not st.session_state["nicho_seleccionado"]:
            st.subheader("📂 Nichos")

            filtro_nicho = st.text_input("Buscar por nombre de nicho", placeholder="Ej: restaurantes")
            filtrados = [n for n in ln if filtro_nicho.lower() in n["nicho_original"].lower()] if filtro_nicho else ln

            if not filtrados:
                st.info("No se encontraron nichos con ese nombre.")
            else:
                for n in filtrados:
                    nombre = n["nicho_original"]
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
                    prioridad = cols_f[1].selectbox("🔥 Prioridad", ["alta", "media", "baja"], key="p_nicho")
                    if st.form_submit_button("💾 Crear tarea"):
                        if texto.strip():
                            if not tiene_suscripcion_activa(plan):
                                st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                                subscription_cta()
                            else:
                                cached_post(
                                    "tarea_lead",
                                    st.session_state.token,
                                    payload={
                                        "texto": texto.strip(),
                                        "tipo": "nicho",
                                        "nicho": nk["nicho"],
                                        "fecha": fecha.strftime("%Y-%m-%d") if fecha else None,
                                        "prioridad": prioridad
                                    }
                                )
                                limpiar_cache()  # ✅ Limpia la caché para reflejar el cambio
                                st.success("Tarea creada ✅")
                                st.rerun()
                        else:
                            st.warning("La descripción es obligatoria.")

            tareas_n = [t for t in todos if t.get("tipo") == "nicho" and t.get("nicho") == nk["nicho"] and not t.get("completado", False)]
            st.markdown("#### 📋 Tareas activas")
            render_list(tareas_n, f"n{nk['nicho']}")

            # Toggle historial
            if st.toggle("📜 Ver historial de tareas de este nicho", key="toggle_historial_nicho"):
                hist_n = cached_get(
                    "historial_tareas",
                    st.session_state.token,
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
elif seccion == titles[3]:

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
                st.session_state.token,
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
                prioridad = cols_f[1].selectbox("🔥 Prioridad", ["alta", "media", "baja"], key="prio_detalle")
                if st.form_submit_button("💾 Crear tarea"):
                    if texto.strip():
                        if not tiene_suscripcion_activa(plan):
                            st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                            subscription_cta()
                        else:
                            cached_post(
                                "tarea_lead",
                                st.session_state.token,
                                payload={
                                    "texto": texto.strip(),
                                    "tipo": "lead",
                                    "dominio": norm,
                                    "fecha": fecha.strftime("%Y-%m-%d") if fecha else None,
                                    "prioridad": prioridad
                                }
                            )
                            st.success("Tarea creada ✅")
                            st.rerun()
                    else:
                        st.warning("La descripción es obligatoria.")

        # Toggle info extra
        if st.toggle("📝 Información extra del lead", key="toggle_info"):
            info = cached_get(
                "info_extra",
                st.session_state.token,
                query={"dominio": norm},
                nocache_key=time.time()
            ) or {}
            with st.form(key="form_info_extra_detalle"):
                c1, c2 = st.columns(2)
                email_nuevo = c1.text_input("📧 Email", value=info.get("email", ""), key="email_info")
                tel_nuevo = c2.text_input("📞 Teléfono", value=info.get("telefono", ""), key="tel_info")
                info_nueva = st.text_area("🗒️ Información libre", value=info.get("informacion", ""), key="nota_info")
                if st.form_submit_button("💾 Guardar información"):
                    if not tiene_suscripcion_activa(plan):
                        st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                        subscription_cta()
                    else:
                        respuesta = cached_post(
                            "guardar_info_extra",
                            st.session_state.token,
                            payload={
                                "dominio": norm,
                                "email": email_nuevo,
                                "telefono": tel_nuevo,
                                "informacion": info_nueva
                            }
                        )
                        if respuesta and respuesta.get("mensaje"):
                            limpiar_cache()  # ✅ Limpia la caché para que se vea la información actualizada
                            st.success("Información guardada correctamente ✅")
                            st.rerun()

        st.markdown("#### 📋 Tareas activas")
        tareas_datos = cached_get(
            "tareas_lead",
            st.session_state.token,
            query={"dominio": norm},
            nocache_key=time.time()
        )
        tareas_l = tareas_datos.get("tareas", []) if tareas_datos else []
        render_list(
            [t for t in tareas_l if not t.get("completado", False)],
            f"lead_t_{norm}"
        )

        st.markdown("#### 📜 Historial")
        hist_datos = cached_get(
            "historial_lead",
            st.session_state.token,
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