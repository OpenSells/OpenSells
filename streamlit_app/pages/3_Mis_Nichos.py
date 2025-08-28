# 3_Mis_Nichos.py – Página de gestión de nichos y leads
#
# ✔️  Correcciones principales
#   1. El buscador global solo está visible cuando se muestran **todos** los nichos,
#      así evitamos que el usuario lo confunda con el filtro interno.
#   2. La vista de “solo nicho” se mantiene tras:
#        • borrar un lead
#        • usar el filtro interno de ese nicho
#      (solo desaparece al pulsar “Volver a todos los nichos” o al borrar el nicho completo).
#   3. Eliminado el bloque duplicado de `st.experimental_rerun()` que provocaba
#      reruns innecesarios.
#   4. Limpieza y tipado ligero.

import os
import streamlit as st
import hashlib
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

from streamlit_app.cache_utils import (
    cached_get,
    cached_post,
    cached_delete,
    limpiar_cache,
)
from streamlit_app.plan_utils import tiene_suscripcion_activa, subscription_cta
from streamlit_app.utils.auth_utils import ensure_session_or_redirect, clear_session
from streamlit_app.utils.cookies_utils import init_cookie_manager_mount
from streamlit_app.utils import http_client

init_cookie_manager_mount()

# ── Config ───────────────────────────────────────────
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
st.set_page_config(page_title="Mis Nichos", page_icon="📁")

st.markdown(
    """
    <style>
    .badge {padding:0.1rem 0.4rem;border-radius:4px;font-size:0.75rem;}
    .badge-warn {background-color:#fff3cd;color:#664d03;}
    .badge-info {background-color:#cfe2ff;color:#084298;}
    .badge-ok {background-color:#d1e7dd;color:#0f5132;}
    </style>
    """,
    unsafe_allow_html=True,
)


ensure_session_or_redirect("Home")
token = st.session_state.get("auth_token")
user = st.session_state.get("user")
if not user:
    resp_user = http_client.get("/me")
    if resp_user is not None and resp_user.status_code == 200:
        user = resp_user.json()
        st.session_state["user"] = user
plan = (user or {}).get("plan", "free")

ESTADOS = {
    "pendiente": ("Pendiente", "🟡"),
    "contactado": ("Contactado", "🟦"),
    "cerrado": ("Cerrado", "🟢"),
    "fallido": ("Fallido", "🔴"),
}

st.markdown(
    """
<style>
.estado-chip{display:inline-block;padding:.25rem .5rem;border-radius:999px;font-weight:600;border:1px solid #F2E5A3;background:#FFF7D1;color:#7A5B00;cursor:pointer;}
</style>
""",
    unsafe_allow_html=True,
)

def _estado_chip_label(estado:str)->str:
    label,icon=ESTADOS.get(estado,("Pendiente","🟡"))
    return f"{icon} {label}"

def _cambiar_estado_lead(lead:dict,lead_id:int,nuevo:str):
    antiguo=lead.get("estado_contacto")
    lead["estado_contacto"]=nuevo
    resp = http_client.patch(
        f"/leads/{lead_id}/estado_contacto",
        json={"estado_contacto": nuevo},
    )
    if not resp or resp.status_code>=400:
        lead["estado_contacto"]=antiguo
        st.toast("No se pudo actualizar el estado",icon="⚠️")
    else:
        st.toast("Estado actualizado",icon="✅")

if st.sidebar.button("Cerrar sesión", type="secondary", use_container_width=True):
    clear_session(preserve_logout_flag=True)
    st.query_params.clear()
    try:
        st.switch_page("Home")
    except Exception:
        st.rerun()

# ── Helpers ──────────────────────────────────────────
def normalizar_nicho(texto: str) -> str:
    import unicodedata
    import re

    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")

def normalizar_dominio(url: str) -> str:
    if not url:
        return ""
    url = url if url.startswith(("http://", "https://")) else f"http://{url}"
    return urlparse(url).netloc.replace("www.", "").split("/")[0]

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def render_estado_badge(estado: str) -> str:
    if estado == "pendiente":
        return '<span class="badge badge-warn">Pendiente</span>'
    if estado == "en_proceso":
        return '<span class="badge badge-info">En proceso</span>'
    return '<span class="badge badge-ok">Contactado</span>'


def _cambiar_estado(key: str, dominio: str):
    nuevo = st.session_state.get(key)
    cached_post(
        "leads/estado_contacto",
        token,
        payload={"dominio": dominio, "estado_contacto": nuevo},
    )
    st.session_state["forzar_recarga"] += 1
    st.rerun()

# ── Forzar Recarga Caché ─────────────────────────────
if "forzar_recarga" not in st.session_state:
    st.session_state["forzar_recarga"] = 0

# ── Título ───────────────────────────────────────────
st.title("📁 Gestión de Nichos")

# ── Búsqueda global (solo en vista “todos los nichos”) ─────────────
if "solo_nicho_visible" not in st.session_state:
    busqueda = st.text_input(
        "🔍 Buscar nichos o leads:",
        value=st.session_state.get("busqueda_global", ""),
        key="input_busqueda_global",
    ).lower().strip()
else:
    # Cuando estamos en vista de un solo nicho no usamos el buscador global
    busqueda = ""

# ── Cargar nichos del backend ───────────────────────
resp = cached_get("mis_nichos", token)
nichos: list[dict] = []
if resp:
    nichos = resp.get("nichos", [])

if not nichos:
    st.info("Aún no tienes nichos guardados.")
    st.stop()

# ── Construir índice rápido de leads (para búsquedas globales) ────
todos_leads = []
for n in nichos:
    datos = cached_get("leads_por_nicho", token, query={"nicho": n["nicho"]})
    leads = datos.get("leads", []) if datos else []
    n["total_leads"] = len(leads)

    for idx, l in enumerate(leads):
        d = normalizar_dominio(l["url"])
        todos_leads.append(
            {
                "dominio": d,
                "nicho": n["nicho"],
                "nicho_original": n["nicho_original"],
                "key": md5(f"{d}_{idx}"),
            }
        )

# ── Resultados del buscador global ──────────────────
if busqueda:
    st.session_state["busqueda_global"] = busqueda
    st.markdown("---")
    st.subheader("🔎 Resultados de búsqueda")

    leads_coinc = [l for l in todos_leads if busqueda in l["dominio"]]
    nichos_coinc = [n for n in nichos if busqueda in n["nicho_original"].lower()]

    # Leads coincidentes
    for idx, l in enumerate(leads_coinc):
        if st.button(
            f"🌐 {l['dominio']} → {l['nicho_original']}",
            key=f"lead_{l['key']}_{idx}",
        ):
            st.session_state["solo_nicho_visible"] = l["nicho"]
            st.session_state["busqueda_global"] = ""
            st.rerun()

    # Nichos coincidentes (solo listamos, sin interacción de momento)
    for n in nichos_coinc:
        st.markdown(f"📂 {n['nicho_original']}")

    st.stop()  # solo mostramos resultados, no renderizamos nada más

# ── Botón «Volver a todos los nichos» ───────────────
if "solo_nicho_visible" in st.session_state:
    if st.button("🔙 Volver a todos los nichos", key="volver_todos"):
        st.session_state.pop("solo_nicho_visible")
        st.session_state.pop("busqueda_global", None)
        st.rerun()

# ── Definir qué nichos se muestran ──────────────────
if "solo_nicho_visible" in st.session_state:
    nichos_visibles = [
        n for n in nichos if n["nicho"] == st.session_state["solo_nicho_visible"]
    ]
else:
    nichos_visibles = nichos

# ── Render de nichos y leads ────────────────────────
for n in nichos_visibles:
    key_exp = f"expandir_{n['nicho']}"
    expanded_por_defecto = "solo_nicho_visible" in st.session_state
    expanded = st.session_state.get(key_exp, expanded_por_defecto)

    with st.expander(
        f"📂 {n['nicho_original']} ({n['total_leads']} leads)",
        expanded=expanded,
    ):
        top_cols = st.columns([8, 2])

        # ── Descargar CSV ───────────────────────────
        try:
            params_export = {"nicho": n["nicho"]}
            if estado_filtro != "todos":
                params_export["estado_contacto"] = estado_filtro
            resp = requests.get(
                f"{BACKEND_URL}/exportar_leads_nicho",
                headers={"Authorization": f"Bearer {token}"},
                params=params_export,
            )
            if resp.status_code == 200:
                top_cols[0].download_button(
                    "📥 Descargar CSV",
                    resp.content,
                    file_name=f"{n['nicho_original']}.csv",
                    mime="text/csv",
                    key=f"csv_{n['nicho']}",
                )
        except Exception:
            pass

        # ── Eliminar nicho ──────────────────────────
        if top_cols[1].button("🗑 Eliminar nicho", key=f"del_nicho_{n['nicho']}"):
            if not tiene_suscripcion_activa(plan):
                st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                subscription_cta()
            else:
                res = cached_delete("eliminar_nicho", token, params={"nicho": n["nicho"]})
                if res:
                    st.success("Nicho eliminado correctamente")
                    if st.session_state.get("solo_nicho_visible") == n["nicho"]:
                        st.session_state.pop("solo_nicho_visible", None)
                    st.session_state["forzar_recarga"] += 1
                    limpiar_cache()
                    st.rerun()
                else:
                    st.error("Error al eliminar el nicho")

        estado_filtro = st.selectbox(
            "Estado de contacto",
            ["todos", "pendiente", "en_proceso", "contactado"],
            key=f"estado_filtro_{n['nicho']}",
        )
        query_params = {"nicho": n["nicho"]}
        if estado_filtro != "todos":
            query_params["estado_contacto"] = estado_filtro
        resp_leads = cached_get(
            "leads_por_nicho",
            token,
            query=query_params,
            nocache_key=st.session_state["forzar_recarga"],
        )
        leads = resp_leads.get("leads", []) if resp_leads else []

        # ── Filtro interno por dominio ───────────────
        filtro = st.text_input(
            "Filtrar leads por dominio:",
            key=f"filtro_{n['nicho']}",
            placeholder="Ej. clinicadental.com",
        ).lower().strip()

        if filtro:
            if not tiene_suscripcion_activa(plan):
                st.warning(
                    "La búsqueda de leads está disponible solo para usuarios con suscripción activa."
                )
                subscription_cta()
            else:
                leads = [
                    l for l in leads
                    if filtro in normalizar_dominio(l["url"]).lower()
                ]

        st.markdown(f"### Total mostrados: {len(leads)}")

        # ── Añadir lead manual (compacto con toggle) ───────────────
        mostrar_form = st.toggle("➕ Añadir Lead Manualmente", key=f"toggle_lead_{n['nicho']}")
        if mostrar_form:
            with st.form(key=f"form_lead_manual_{n['nicho']}"):
                c1, c2 = st.columns(2)
                dominio_manual = c1.text_input("🌐 Dominio", key=f"dom_{n['nicho']}")
                email_manual = c2.text_input("📧 Email", key=f"email_{n['nicho']}")
                telefono_manual = c1.text_input("📞 Teléfono", key=f"tel_{n['nicho']}")
                nombre_manual = c2.text_input("🏷️ Nombre", key=f"nombre_{n['nicho']}")

                submitted = st.form_submit_button("✅ Añadir")

                if submitted:
                    if not dominio_manual:
                        st.warning("Debes introducir al menos el dominio.")
                    else:
                        dominio_normalizado = normalizar_dominio(dominio_manual)
                        dominios_existentes = {l["dominio"] for l in todos_leads}

                        if dominio_normalizado in dominios_existentes:
                            st.markdown(
                                """
                                <style>
                                .small-note { font-size: 0.85rem; opacity: 0.85; margin-top: -0.25rem; }
                                </style>
                                <div class="small-note">Este lead ya existe en tu sistema (no se duplicará).</div>
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            if not tiene_suscripcion_activa(plan):
                                st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                                subscription_cta()
                            else:
                                res = cached_post(
                                    "añadir_lead_manual",
                                    token,
                                    payload={
                                        "dominio": dominio_manual,
                                        "email": email_manual,
                                        "telefono": telefono_manual,
                                        "nombre": nombre_manual,
                                        "nicho": n["nicho_original"]
                                    }
                                )
                                if res:
                                    st.success("Lead añadido correctamente ✅")
                                    st.session_state["forzar_recarga"] += 1
                                    st.session_state["solo_nicho_visible"] = n["nicho"]
                                    st.session_state[key_exp] = True
                                    st.rerun()
                                else:
                                    st.error("Error al guardar el lead")

        if "lead_a_mover" not in st.session_state:
            st.session_state["lead_a_mover"] = None

        for i, l in enumerate(leads):
            dominio = normalizar_dominio(l["url"])
            estado_actual = l.get("estado_contacto", "pendiente")
            clave_base = f"{dominio}_{n['nicho']}_{i}".replace(".", "_")
            cols_row = st.columns([4, 2, 2, 2, 2, 2])
            cols_row[0].markdown(
                f"- 🌐 [**{dominio}**](https://{dominio})",
                unsafe_allow_html=True,
            )
            estado_label = _estado_chip_label(estado_actual)
            with cols_row[1]:
                with st.popover(estado_label, help="Cambiar estado", use_container_width=False):
                    for est in ESTADOS.keys():
                        if st.button(_estado_chip_label(est), key=f"btn_est_{est}_{clave_base}"):
                            _cambiar_estado_lead(l, l.get("id"), est)
                            st.rerun()

            with cols_row[5]:
                with st.popover("➕ Tarea", help="Agregar tarea", use_container_width=False):
                    texto = st.text_area("Descripción", key=f"tarea_txt_{clave_base}")
                    fecha = st.date_input("Fecha", value=None, key=f"tarea_fecha_{clave_base}")
                    prioridad = st.selectbox("Prioridad", ["alta", "media", "baja"], index=1, key=f"tarea_prio_{clave_base}")
                    if st.button("Guardar", key=f"tarea_save_{clave_base}"):
                        if texto.strip():
                            resp = http_client.post(
                                "/tareas",
                                json={
                                    "texto": texto.strip(),
                                    "fecha": fecha.strftime("%Y-%m-%d") if fecha else None,
                                    "prioridad": prioridad,
                                    "tipo": "lead",
                                    "dominio": dominio,
                                    "nicho": n["nicho"],
                                    "auto": False,
                                },
                            )
                            if resp and resp.status_code < 400:
                                st.toast("Tarea creada", icon="✅")
                                st.rerun()
                            else:
                                st.toast("No se pudo crear la tarea", icon="⚠️")
                        else:
                            st.warning("La descripción es obligatoria")

            # Botón eliminar
            if cols_row[2].button("🗑 Borrar", key=f"btn_borrar_{clave_base}", use_container_width=False):
                if not tiene_suscripcion_activa(plan):
                    st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                    subscription_cta()
                else:
                    res = cached_delete(
                        "eliminar_lead",
                        token,
                        params={
                            "nicho": n["nicho"],
                            "dominio": dominio,
                            "solo_de_este_nicho": True,
                        },
                    )
                    if res:
                        st.session_state["forzar_recarga"] += 1
                        st.session_state[key_exp] = True
                        st.session_state["solo_nicho_visible"] = n["nicho"]
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar el lead")

            # Botón Mover compacto
            if cols_row[3].button("🔀 Mover", key=f"btn_mostrar_mover_{clave_base}", use_container_width=False):
                st.session_state["lead_a_mover"] = clave_base

            # Formulario de mover lead si está activo
            if st.session_state.get("lead_a_mover") == clave_base:
                nichos_destino = [ni["nicho_original"] for ni in nichos if ni["nicho"] != n["nicho"]]
                nuevo_nicho = st.selectbox("Mover a:", nichos_destino, key=f"select_nuevo_nicho_{clave_base}")

                if st.button("✅ Confirmar", key=f"confirmar_mover_{clave_base}"):
                    if not tiene_suscripcion_activa(plan):
                        st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                        subscription_cta()
                    else:
                        res = cached_post(
                            "mover_lead",
                            token,
                            payload={
                                "dominio": dominio,
                                "origen": n["nicho_original"],
                                "destino": nuevo_nicho
                            }
                        )
                        if res:
                            st.success("Lead movido correctamente ✅")
                            st.session_state["forzar_recarga"] += 1
                            st.session_state["lead_a_mover"] = None
                            st.session_state["solo_nicho_visible"] = normalizar_nicho(nuevo_nicho)
                            st.rerun()
                        else:
                            st.error("Error al mover lead")

            # Botón Información extra
            if cols_row[4].button("📝 Notas", key=f"btn_info_{clave_base}", use_container_width=False):
                st.session_state[f"mostrar_info_{clave_base}"] = not st.session_state.get(f"mostrar_info_{clave_base}", False)

            # Formulario de info extra si está activado
            if st.session_state.get(f"mostrar_info_{clave_base}", False):
                info = cached_get("info_extra", token, query={"dominio": dominio}, nocache_key=st.session_state["forzar_recarga"]) or {}

                with st.form(key=f"form_info_extra_{clave_base}"):
                    c1, c2 = st.columns(2)
                    email_nuevo = c1.text_input("📧 Email", value=info.get("email", ""), key=f"email_{clave_base}")
                    tel_nuevo = c2.text_input("📞 Teléfono", value=info.get("telefono", ""), key=f"tel_{clave_base}")
                    info_nueva = st.text_area("📝 Información libre", value=info.get("informacion", ""), key=f"info_{clave_base}")

                    if st.form_submit_button("💾 Guardar información"):
                        if not tiene_suscripcion_activa(plan):
                            st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
                            subscription_cta()
                        else:
                            res = cached_post(
                                "guardar_info_extra",
                                token,
                                payload={
                                    "dominio": dominio,
                                    "email": email_nuevo,
                                    "telefono": tel_nuevo,
                                    "informacion": info_nueva
                                }
                            )
                            if res:
                                st.success("Información guardada correctamente ✅")
                                st.session_state["forzar_recarga"] += 1
                                st.rerun()
