# 3_Mis_Nichos.py – Página de gestión de nichos y leads
#
# ✔️  Correcciones principales
#   1. El buscador global solo está visible cuando se muestran **todos** los nichos,
#      así evitamos que el usuario lo confunda con el filtro interno.
#   2. La vista de “solo nicho” se mantiene tras:
#        • borrar un lead
#        • usar el filtro interno de ese nicho
#      (solo desaparece al pulsar “Volver a todos los nichos” o al borrar el nicho completo).
#   3. Limpieza y tipado ligero.

import os
import logging
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
from streamlit_app.plan_utils import resolve_user_plan, tiene_suscripcion_activa, subscription_cta
import streamlit_app.utils.http_client as http_client
from streamlit_app.utils.auth_session import (
    is_authenticated,
    remember_current_page,
    get_auth_token,
    clear_auth_token,
    clear_page_remember,
)
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.utils.nav import go, HOME_PAGE

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


PAGE_NAME = "Nichos"
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
plan = resolve_user_plan(token)["plan"]

with st.sidebar:
    logout_button()

ESTADOS = {
    "pendiente": ("Pendiente", "🟡"),
    "en_proceso": ("En proceso", "🟠"),
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
    """Actualiza el estado del lead contra el backend con fallback defensivo."""

    antiguo=lead.get("estado_contacto")
    if antiguo==nuevo:
        return

    lead["estado_contacto"]=nuevo
    endpoint=f"/leads/{lead_id}/estado_contacto"
    payload={"estado_contacto": nuevo}

    try:
        patch_method=getattr(http_client,"patch",None)
        if callable(patch_method):
            resp=patch_method(endpoint,json=payload,timeout=20)
        else:
            base_url=(BACKEND_URL or getattr(http_client, "BASE_URL", "")).rstrip("/")
            token_actual=get_auth_token()
            headers={"Authorization":f"Bearer {token_actual}"} if token_actual else {}
            resp=requests.patch(f"{base_url}{endpoint}",json=payload,headers=headers,timeout=20)
    except Exception:
        lead["estado_contacto"]=antiguo
        st.toast("No se pudo actualizar el estado (error de red).",icon="⚠️")
        logging.exception("Error al actualizar estado de lead %s", lead_id)
        return

    status=getattr(resp,"status_code",None)
    body=""
    if isinstance(resp,dict):
        status=resp.get("_status")
        body=resp.get("_error") or ""
        if resp.get("_error") == "unauthorized":
            lead["estado_contacto"]=antiguo
            st.toast("Sesión expirada. Vuelve a iniciar sesión.",icon="⚠️")
            return
    else:
        body=getattr(resp,"text","")

    if not status or status>=400:
        lead["estado_contacto"]=antiguo
        cuerpo=body[:400] if body else ""
        codigo=status if status is not None else "¿?"
        st.toast(f"Error {codigo} al actualizar el estado. {cuerpo}",icon="⚠️")
        return

    st.toast("Estado actualizado",icon="✅")


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


def _extract_nichos(data) -> list[dict]:
    if not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nichos_list = data.get("nichos")
        if isinstance(nichos_list, list):
            return nichos_list
    return []


def _extract_leads(data) -> list[dict]:
    if not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items
        leads = data.get("leads")
        if isinstance(leads, list):
            return leads
    return []


def _nicho_original_value(nicho: dict) -> str:
    return nicho.get("nicho_original") or nicho.get("nicho") or ""


def render_estado_badge(estado: str) -> str:
    if estado == "pendiente":
        return '<span class="badge badge-warn">Pendiente</span>'
    if estado == "en_proceso":
        return '<span class="badge badge-info">En proceso</span>'
    return '<span class="badge badge-ok">Contactado</span>'


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
resp = cached_get("/mis_nichos", token)
nichos: list[dict] = _extract_nichos(resp)

if not nichos:
    st.info("Aún no tienes nichos guardados.")
    st.stop()

# ── Construir índice rápido de leads (para búsquedas globales) ────
todos_leads = []
for n in nichos:
    datos = cached_get("leads_por_nicho", token, query={"nicho": n["nicho"]})
    leads = _extract_leads(datos)
    n["total_leads"] = datos.get("count", len(leads)) if isinstance(datos, dict) else len(leads)
    original = _nicho_original_value(n)

    for idx, l in enumerate(leads):
        url_val = l.get("url") or l.get("dominio") or ""
        d = normalizar_dominio(url_val)
        todos_leads.append(
            {
                "dominio": d,
                "nicho": n["nicho"],
                "nicho_original": l.get("nicho_original") or original,
                "key": md5(f"{d}_{idx}"),
            }
        )

# ── Resultados del buscador global ──────────────────
if busqueda:
    st.session_state["busqueda_global"] = busqueda
    st.markdown("---")
    st.subheader("🔎 Resultados de búsqueda")

    leads_coinc = [l for l in todos_leads if busqueda in l["dominio"]]
    nichos_coinc = [n for n in nichos if busqueda in _nicho_original_value(n).lower()]

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
        st.markdown(f"📂 {_nicho_original_value(n)}")

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
    original = _nicho_original_value(n)

    with st.expander(
        f"📂 {original} ({n['total_leads']} leads)",
        expanded=expanded,
    ):
        top_cols = st.columns([8, 2])

        # ── Descargar CSV ───────────────────────────
        try:
            params_export = {"nicho": n["nicho"]}
            estado_actual = st.session_state.get(f"estado_filtro_{n['nicho']}", "todos")
            if estado_actual != "todos":
                params_export["estado_contacto"] = estado_actual
            resp = requests.get(
                f"{BACKEND_URL}/exportar_leads_nicho",
                headers={"Authorization": f"Bearer {token}"},
                params=params_export,
            )
            if resp.status_code == 200:
                top_cols[0].download_button(
                    "📥 Descargar CSV",
                    resp.content,
                    file_name=f"{original}.csv",
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
        leads = _extract_leads(resp_leads)

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
                    l
                    for l in leads
                    if filtro in normalizar_dominio(l.get("url") or l.get("dominio")).lower()
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
                                        "nicho": original,
                                    },
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
            url_value = l.get("url") or l.get("dominio") or ""
            dominio = normalizar_dominio(url_value)
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
                nichos_destino = [
                    _nicho_original_value(ni)
                    for ni in nichos
                    if ni["nicho"] != n["nicho"]
                ]
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
                                "origen": original,
                                "destino": nuevo_nicho,
                            },
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
