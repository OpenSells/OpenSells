# 1_Busqueda.py – Página de búsqueda con flujo por pasos, cierre limpio del popup y sugerencias de nicho mejoradas

import re
import streamlit as st
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
from json import JSONDecodeError

import streamlit_app.utils.http_client as http_client

from streamlit_app.cache_utils import (
    cached_get,
    get_openai_client,
    auth_headers,
    limpiar_cache,
)
from streamlit_app.plan_utils import subscription_cta
from streamlit_app.utils.auth_session import (
    is_authenticated,
    remember_current_page,
    get_auth_token,
)
from streamlit_app.utils.logout_button import logout_button
from streamlit_app.ui.account_helpers import fetch_account_overview, get_plan_name
from components.ui import render_whatsapp_fab

load_dotenv()

st.set_page_config(page_title="Buscar Leads", page_icon="🔎", layout="centered")

PAGE_NAME = "Leads"
remember_current_page(PAGE_NAME)
if not is_authenticated():
    st.title(PAGE_NAME)
    st.info("Inicia sesión en la página Home para continuar.")
    st.stop()

BACKEND_URL = http_client.BASE_URL

token = get_auth_token()
me, usage, quotas, _ = fetch_account_overview(token) if token else ({}, {}, {}, {})
user = me
st.session_state["user"] = user
plan_name = get_plan_name(me)


with st.sidebar:
    logout_button()

# -------------------- Helpers --------------------



EXTENDED_PREFIX = "[Búsqueda extendida] "
MAX_VARIANTS = 3
VIEW_KEY = "variantes_selector_ids_view"
CANON_KEY = "variantes_selector_ids"


def _pretty_variant_label(v: str) -> str:
    """Genera la etiqueta visible ocultando operadores sin perder el prefijo."""

    prefix = ""
    if v.startswith(EXTENDED_PREFIX):
        prefix = EXTENDED_PREFIX
        v = v[len(prefix) :]

    cleaned = re.sub(r"(\s|^)-(?:site|inurl|intitle|intext):\S+", "", v).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return f"{prefix}{cleaned}" if prefix else cleaned


def normalizar_dominio(url):
    if not url:
        return ""
    u = url if url.startswith("http") else f"http://{url}"
    return urlparse(u).netloc.replace("www.", "").split("/")[0]

def safe_json(resp: requests.Response) -> dict:
    try:
        return resp.json()
    except JSONDecodeError:
        st.error(f"Respuesta no válida: {resp.text}")
        return {}


LIMIT_MESSAGES = {
    "searches": "Has agotado tus 4 búsquedas del plan Free este mes.",
    "lead_credits": "Sin créditos de leads (plan de pago).",
    "ai": "Has alcanzado el límite diario de IA.",
    "csv_exports": "Has alcanzado el límite de exportaciones.",
}


def mostrar_banner_limite(detail: dict | None):
    if not isinstance(detail, dict):
        st.warning("🚫 No tienes permiso para continuar con esta acción.")
        return
    resource = detail.get("resource")
    mensaje = LIMIT_MESSAGES.get(resource) or "🚫 No tienes permiso para continuar con esta acción."
    st.warning(mensaje)
    if resource in {"lead_credits", "csv_exports"}:
        subscription_cta()


def _set_variantes_from_response(data: dict | None):
    data = data or {}
    variantes_reales = data.get("variantes") or data.get("variantes_generadas") or []
    variantes_display = data.get("variantes_display") or variantes_reales
    st.session_state.variantes = variantes_reales
    st.session_state.variantes_display = variantes_display
    st.session_state.has_extended_variant = bool(data.get("has_extended_variant"))
    st.session_state.extended_index = data.get("extended_index")
    st.session_state.seleccionadas = []
    st.session_state.seleccion_display = []
    st.session_state[CANON_KEY] = []
    st.session_state[VIEW_KEY] = []

# -------------------- Flags iniciales --------------------
for flag, valor in {
    "loading": False,
    "estado_actual": "",
    "fase_extraccion": None,
    "guardando_mostrado": False,
    "guardar_realizado": False,
    "export_realizado": False,
    "mostrar_resultado": False,
    "dominios": [],
    "variantes_display": [],
    "has_extended_variant": False,
    "extended_index": None,
    "seleccionadas": [],
    "seleccion_display": [],
    VIEW_KEY: [],
    CANON_KEY: [],
    "limit_error_detail": None,
    "truncated_free": False,
}.items():
    st.session_state.setdefault(flag, valor)

headers = auth_headers(token)

if st.session_state.get("limit_error_detail"):
    mostrar_banner_limite(st.session_state.get("limit_error_detail"))


# -------------------- Popup --------------------

def mostrar_popup():
    mensaje = st.session_state.get("estado_actual", "⏳ Extrayendo leads, por favor espera...")
    st.markdown(
        f"""
    <div style='position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.35); z-index: 999;'>
        <div style='position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: #d6ecff; border: 1px solid #9ec5fe; padding: 2rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.15);'>
            <h4 style='color: #084298; margin:0;'>⏳ No cierres esta ventana</h4>
            <p style='margin-top: .5rem'>El proceso puede tardar unos minutos.</p>
            <p style='font-weight: 600; margin-top: 1.2rem;'>{mensaje}</p>
            <div class='loader' style='margin: 20px auto; border: 4px solid #f3f3f3; border-top: 4px solid #084298; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite;'></div>
        </div>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    """,
        unsafe_allow_html=True,
    )

# -------------------- Proceso principal --------------------

def procesar_extraccion():
    fase = st.session_state.get("fase_extraccion", "buscando")

    # 1. Buscar dominios --------------------------------------------------
    if fase == "buscando":
        st.session_state.estado_actual = "Buscando dominios"
        r = requests.post(
            f"{BACKEND_URL}/buscar_variantes_seleccionadas",
            json={"variantes": st.session_state.seleccionadas},
            headers=headers,
        )
        data = safe_json(r) if r is not None else {}
        detail = ""
        if isinstance(data, dict):
            detail = str(data.get("detail") or "")
        if r.status_code == 200:
            dominios = data.get("dominios", [])
            if not dominios:
                st.warning(
                    "No se encontraron dominios para las variantes. Prueba con otras variantes o añade una ‘Búsqueda extendida’."
                )
                st.session_state.loading = False
                st.session_state.estado_actual = ""
                return
            st.session_state.dominios = dominios
            st.session_state.fase_extraccion = "extrayendo"
            st.rerun()
        else:
            if (
                r.status_code == 503
                or "BRAVE_API_KEY" in detail
                or "Busqueda no configurada" in detail
            ):
                st.warning(
                    "⚙️ Debes configurar la variable BRAVE_API_KEY en el backend para habilitar las búsquedas."
                )
                st.session_state.loading = False
                st.session_state.estado_actual = ""
                return
            if r.status_code == 502:
                st.warning(
                    "No se encontraron dominios para las variantes. Prueba con otras variantes o añade una ‘Búsqueda extendida’."
                )
                st.session_state.loading = False
                st.session_state.estado_actual = ""
                return
            st.error("Error al buscar dominios")
            st.session_state.loading = False
            return

    # 2. Extraer datos ----------------------------------------------------
    if fase == "extrayendo":
        if not st.session_state.dominios:
            st.warning(
                "No hay dominios disponibles para extraer leads. Intenta nuevamente con otras variantes."
            )
            st.session_state.loading = False
            st.session_state.estado_actual = ""
            return
        if not st.session_state.get("extraccion_realizada"):
            st.session_state.estado_actual = "Extrayendo datos"
            st.session_state.extraccion_realizada = True
            st.rerun()

        r = requests.post(
            f"{BACKEND_URL}/extraer_multiples",
            json={"urls": [f"https://{d}" for d in st.session_state.dominios], "pais": "ES"},
            headers=headers,
        )
        if r.status_code == 200:
            data = safe_json(r)
            st.session_state.payload_export = data.get("payload_export", {})
            st.session_state.payload_export["nicho"] = st.session_state.nicho_actual  # ✅ necesario para evitar error 422
            st.session_state.resultados = data.get("resultados", [])
            st.session_state.truncated_free = bool(data.get("truncated"))
            st.session_state.limit_error_detail = None
            limpiar_cache()
            st.session_state.fase_extraccion = "exportando"
            st.rerun()
        elif r.status_code == 403:
            data = safe_json(r)
            detail = data.get("detail") if isinstance(data, dict) else None
            st.session_state.limit_error_detail = detail
            st.session_state.truncated_free = False
            mostrar_banner_limite(detail)
            st.session_state.loading = False
            st.session_state.estado_actual = ""
            st.session_state.fase_extraccion = None
            st.session_state.extraccion_realizada = False
            return
        else:
            st.error("Error al extraer los datos")
            st.session_state.loading = False
            return

    # 3. Guardar leads ----------------------------------------------------
    if fase == "exportando":
        if not st.session_state.guardando_mostrado:
            st.session_state.estado_actual = "Guardando leads en tu cuenta…"
            st.session_state.guardando_mostrado = True
            st.rerun()

        if not st.session_state.get("guardar_realizado"):
            payload_guardar = {
                "nicho": st.session_state.nicho_actual,
                "nicho_original": st.session_state.nicho_actual,
                "items": st.session_state.resultados,
            }
            r_save = requests.post(
                f"{BACKEND_URL}/guardar_leads",
                json=payload_guardar,
                headers=headers,
                timeout=120,
            )
            st.session_state.guardar_realizado = True

            if r_save.status_code != 200:
                st.error("No se pudieron guardar los leads en la base de datos.")
                st.session_state.loading = False
                st.stop()

        if not st.session_state.get("export_realizado"):
            r = requests.post(
                f"{BACKEND_URL}/exportar_csv",
                json=st.session_state.payload_export,
                headers=headers,
                timeout=120,
            )
            st.session_state.export_exitoso = r.status_code == 200
            st.session_state.export_realizado = True

        st.session_state.loading = False
        st.session_state.mostrar_resultado = True
        st.rerun()

# -------------------- Cuando está cargando --------------------
if st.session_state.loading:
    mostrar_popup()
    procesar_extraccion()
    st.stop()

# -------------------- UI Principal (solo si no está cargando) -----------

st.title("🎯 Encuentra tus próximos clientes")

st.markdown(
    """
<style>
.red-help { color: #d00000 !important; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)

with st.expander("❓ Consejos para obtener mejores leads", expanded=False):
    st.markdown(
        "- **Los leads no se repiten, prueba varias veces la misma búsqueda para obtener más resultados.**\n"
        "- Usa palabras clave específicas + ciudad.\n"
        "- Evita términos genéricos (ej. \"mejor\", \"barato\") sin contexto.\n"
        "- Prueba 2–3 variantes por nicho.\n"
        "- Filtra dominios repetidos y revisa emails sospechosos."
    )

memoria_data = cached_get("/mi_memoria", token)
memoria = memoria_data.get("memoria", "") if memoria_data else ""

nichos_data = cached_get("/mis_nichos", token)
if isinstance(nichos_data, list):
    nichos_lista_base = nichos_data
elif isinstance(nichos_data, dict):
    nichos_lista_base = nichos_data.get("nichos", [])
else:
    nichos_lista_base = []
lista_nichos = [n.get("nicho") for n in nichos_lista_base]
lista_nichos = [n for n in lista_nichos if n]
lista_nichos = lista_nichos or []

cliente_ideal = st.text_input(
    "¿Cómo es tu cliente ideal?",
    placeholder="Ej: clínicas dentales en Valencia",
    key="cliente_ideal",
)


def _sugerencias(cliente_txt: str):
    # TODO(Ayrton): si existe una función real, usarla. Esto es fallback:
    base = [
        "Dentistas en Madrid",
        "Fisioterapeutas Barcelona",
        "Abogados Valencia",
        "Clínicas Estéticas Sevilla",
    ]
    if cliente_txt and len(cliente_txt.strip()) >= 3:
        return [s for s in base if cliente_txt.lower() in s.lower()] or base
    return base

OPCION_PLACEHOLDER = "— Selecciona un nicho —"
OPCION_CREAR = "➕ Crear nuevo nicho"

with st.expander("💡 Sugerencias de nichos rentables", expanded=False):
    sugs = _sugerencias(cliente_ideal)
    if sugs:
        st.markdown("\n".join([f"- {s}" for s in sugs]))
    else:
        st.caption("Escribe tu cliente ideal para ver ideas.")

lista_nichos = lista_nichos or []
opciones = [OPCION_PLACEHOLDER, OPCION_CREAR] + lista_nichos

if "nicho_select_val" not in st.session_state:
    st.session_state["nicho_select_val"] = OPCION_PLACEHOLDER

nicho_select_val = st.selectbox(
    "Selecciona un nicho",
    options=opciones,
    index=opciones.index(st.session_state["nicho_select_val"]) if st.session_state["nicho_select_val"] in opciones else 0,
    key="nicho_select_val",
)

nicho_actual = ""
if nicho_select_val == OPCION_CREAR:
    nuevo = st.text_input(
        "Nombre del nicho nuevo",
        key="nuevo_nicho_nombre",
        placeholder="Ej.: Dentistas en Madrid",
    )
    nicho_actual = nuevo.strip()
elif nicho_select_val not in (OPCION_PLACEHOLDER, OPCION_CREAR):
    nicho_actual = nicho_select_val.strip()

if nicho_actual:
    st.session_state.nicho_actual = nicho_actual

# -------------------- Generar variantes --------------------
remaining_searches = None
if plan_name == "free":
    quota_searches = quotas.get("searches_per_month")
    used_searches = usage.get("searches")
    if used_searches is None:
        used_searches = usage.get("leads")
    if isinstance(quota_searches, (int, float)):
        used_val = int(used_searches or 0)
        remaining_searches = max(int(quota_searches) - used_val, 0)
disable_search = plan_name == "free" and remaining_searches is not None and remaining_searches == 0
if plan_name == "free" and remaining_searches is not None:
    st.caption(f"Te quedan {remaining_searches} búsquedas este mes.")
if st.button(
    "🚀 Buscar variantes",
    disabled=disable_search,
    help="Límite de búsquedas alcanzado" if disable_search else None,
):
    if not cliente_ideal.strip() or not nicho_actual:
        st.warning("Completa cliente ideal y nicho para continuar")
    else:
        payload = {"cliente_ideal": f"{cliente_ideal}. {memoria}".strip('.')}
        with st.spinner("Generando variantes con IA..."):
            r = requests.post(f"{BACKEND_URL}/buscar", json=payload, headers=headers)
        if r.status_code == 200:
            data = safe_json(r)
            if "pregunta_sugerida" in data:
                st.session_state.pregunta_sugerida = data["pregunta_sugerida"]
                st.session_state.variantes = []
                st.session_state.variantes_display = []
                st.session_state.has_extended_variant = False
                st.session_state.extended_index = None
            else:
                _set_variantes_from_response(data)

# -------------------- Pregunta de refinamiento --------------------
pregunta_sugerida = (st.session_state.get("pregunta_sugerida") or "").strip()

if pregunta_sugerida and pregunta_sugerida.upper() != "OK.":
    st.info(f"🤖 {pregunta_sugerida}")
    respuesta = st.text_input("Tu respuesta para afinar la búsqueda:", key="respuesta_contextual")
    if st.button("Responder y continuar"):
        payload = {
            "cliente_ideal": cliente_ideal.strip(),
            "contexto_extra": respuesta,
            "forzar_variantes": True,
        }
        with st.spinner("Generando variantes con contexto adicional..."):
            r = requests.post(f"{BACKEND_URL}/buscar", json=payload, headers=headers)
        if r.status_code == 200:
            st.session_state.pregunta_sugerida = None
            _set_variantes_from_response(safe_json(r))

# -------------------- Selección de variantes --------------------
if st.session_state.get("variantes"):
    variantes_internas = st.session_state.get("variantes", [])
    variantes_display = st.session_state.get("variantes_display") or variantes_internas
    option_ids = list(range(len(variantes_display)))

    st.session_state.setdefault(VIEW_KEY, [])
    st.session_state.setdefault(CANON_KEY, [])

    def _limit_variants_on_change():
        sel = st.session_state.get(VIEW_KEY, [])
        if len(sel) > MAX_VARIANTS:
            trimmed = sel[:MAX_VARIANTS]
            st.session_state[VIEW_KEY] = trimmed
            st.session_state[CANON_KEY] = trimmed
            st.rerun()
        else:
            st.session_state[CANON_KEY] = sel

    _ = st.multiselect(
        "Selecciona hasta 3 variantes:",
        options=option_ids,
        key=VIEW_KEY,
        on_change=_limit_variants_on_change,
        format_func=lambda i: _pretty_variant_label(variantes_display[i]),
        help="Puedes elegir hasta 3. La [Búsqueda extendida] amplía la cobertura.",
    )

    valid_ids = set(option_ids)
    if any(i not in valid_ids for i in st.session_state[VIEW_KEY]):
        st.session_state[VIEW_KEY] = [
            i for i in st.session_state[VIEW_KEY] if i in valid_ids
        ]
        st.session_state[CANON_KEY] = st.session_state[VIEW_KEY]

    selected_ids = st.session_state[CANON_KEY]

    if len(selected_ids) > MAX_VARIANTS:
        st.warning("Solo puedes seleccionar hasta 3 variantes.")

    seleccion_interna = [
        variantes_internas[i]
        for i in selected_ids
        if 0 <= i < len(variantes_internas)
    ]
    seleccion_display = [
        variantes_display[i]
        for i in selected_ids
        if 0 <= i < len(variantes_display)
    ]

    st.session_state.seleccion_display = seleccion_display
    st.session_state.seleccionadas = seleccion_interna

    if st.session_state.get("has_extended_variant"):
        st.caption(
            "ℹ️ La **Búsqueda extendida** se añade automáticamente para ampliar la cobertura y encontrar más posibles leads."
        )

    disabled = len(seleccion_interna) == 0
    if st.button("🔎 Buscar dominios", disabled=disabled, key="btn_extraer"):
        if not cliente_ideal.strip() or not nicho_actual:
            st.warning("Completa cliente ideal y nicho para continuar")
        elif not seleccion_interna:
            st.warning("Selecciona al menos una variante")
        else:
            st.session_state.limit_error_detail = None
            st.session_state.truncated_free = False
            st.session_state.fase_extraccion = "buscando"
            st.session_state.loading = True
            st.session_state.procesando = "dominios"
            st.rerun()

# -------------------- Mostrar resultado final debajo del flujo -----------

if st.session_state.get("mostrar_resultado"):
    if st.session_state.get("export_exitoso"):
        st.success("✅ Para trabajar con tus leads, ve a la página **Mis Nichos**.")
    else:
        st.error("Error al guardar/exportar los leads")

    if st.session_state.get("resultados"):
        st.write("✅ Leads extraídos:")
        if st.session_state.get("truncated_free"):
            st.info("🔒 Free: máx 10 leads por búsqueda.")
        st.dataframe(st.session_state.resultados)

    # Limpiar flags para futuras búsquedas
    for flag in [
        "fase_extraccion",
        "guardando_mostrado",
        "guardar_realizado",
        "mostrar_resultado",
        "export_realizado",
        "export_exitoso",
        "extraccion_realizada",
    ]:
        st.session_state.pop(flag, None)

render_whatsapp_fab(phone_e164="+34634159527", default_msg="Necesito ayuda")
