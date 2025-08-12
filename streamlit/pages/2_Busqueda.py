# 2_Busqueda.py – Página de búsqueda con flujo por pasos, cierre limpio del popup y sugerencias de nicho mejoradas

import os
import streamlit as st
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
from json import JSONDecodeError
from utils import http_client

from session_bootstrap import bootstrap
bootstrap()

from cache_utils import cached_get, get_openai_client, auth_headers, limpiar_cache
from auth_utils import ensure_token_and_user, logout_button
from plan_utils import subscription_cta

load_dotenv()

BACKEND_URL = http_client.BACKEND_URL
st.set_page_config(page_title="Buscar Leads", page_icon="🔎", layout="centered")


def api_me(token: str):
    return http_client.get("/me", headers={"Authorization": f"Bearer {token}"})


user, token = ensure_token_and_user(api_me)
if not user:
    st.info("Es necesario iniciar sesión para usar esta sección.")
    try:
        st.page_link("Home.py", label="Ir al formulario de inicio de sesión")
    except Exception:
        if st.button("Ir a Home"):
            try:
                st.switch_page("Home.py")
            except Exception:
                st.info("Navega a la página Home desde el menú de la izquierda.")
    st.stop()

plan = (user or {}).get("plan", "free")

logout_button()

# -------------------- Helpers --------------------



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

# -------------------- Flags iniciales --------------------
for flag, valor in {
    "loading": False,
    "estado_actual": "",
    "fase_extraccion": None,
    "guardando_mostrado": False,
    "mostrar_resultado": False,
}.items():
    st.session_state.setdefault(flag, valor)

headers = auth_headers(st.session_state.token)


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
        if r.status_code == 200:
            data = safe_json(r)
            st.session_state.dominios = data.get("dominios", [])
            st.session_state.fase_extraccion = "extrayendo"
            st.rerun()
        else:
            st.error("Error al buscar dominios")
            st.session_state.loading = False
            return

    # 2. Extraer datos ----------------------------------------------------
    if fase == "extrayendo":
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
            limpiar_cache()
            st.session_state.fase_extraccion = "exportando"
            st.rerun()
        elif r.status_code == 403:
            st.warning("🚫 Tu suscripción no permite extraer leads. Actualiza tu plan para continuar.")
            subscription_cta()
            st.session_state.loading = False
            return
        else:
            st.error("Error al extraer los datos")
            st.session_state.loading = False
            return

    # 3. Guardar leads ----------------------------------------------------
    if fase == "exportando":
        # Mostrar texto "Guardando leads" solo una vez
        if not st.session_state.guardando_mostrado:
            st.session_state.estado_actual = "Guardando leads"
            st.session_state.guardando_mostrado = True
            st.rerun()

        # Ejecutar exportación solo una vez
        if not st.session_state.get("export_realizado"):
            r = requests.post(
                f"{BACKEND_URL}/exportar_csv", json=st.session_state.payload_export, headers=headers
            )
            st.session_state.export_exitoso = r.status_code == 200
            st.session_state.export_realizado = True

        # Finalizar --------------------------------------------------------
        st.session_state.loading = False  # cierra popup en el siguiente rerun
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
        "- Usa palabras clave específicas + ciudad.\n"
        "- Evita términos genéricos (ej. \"mejor\", \"barato\") sin contexto.\n"
        "- Prueba 2–3 variantes por nicho.\n"
        "- Filtra dominios repetidos y revisa emails sospechosos.\n"
        "- Combina búsqueda web con Google Maps."
    )

memoria_data = cached_get("mi_memoria", st.session_state.token)
memoria = memoria_data.get("memoria", "") if memoria_data else ""

nichos_data = cached_get("mis_nichos", st.session_state.token)
lista_nichos = [n["nicho_original"] for n in nichos_data.get("nichos", [])] if nichos_data else []
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
    for i, sug in enumerate(_sugerencias(cliente_ideal)):
        cols = st.columns([1, 6, 2])
        with cols[0]:
            st.write("•")
        with cols[1]:
            st.write(sug)
        with cols[2]:
            if st.button("Usar", key=f"usar_sug_{i}"):
                st.session_state["nuevo_nicho_nombre"] = sug
                st.session_state["nicho_select_val"] = OPCION_CREAR
                st.rerun()

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
if st.button("🚀 Buscar variantes"):
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
            else:
                st.session_state.variantes = data.get("variantes_generadas", [])

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
            st.session_state.variantes = safe_json(r).get("variantes_generadas", [])

# -------------------- Selección de variantes --------------------
if st.session_state.get("variantes"):
    seleccionadas = st.multiselect(
        "Selecciona hasta 3 variantes:",
        st.session_state.variantes,
        default=st.session_state.get("seleccionadas", []),
        max_selections=3,
        key="multiselect_variantes",
        placeholder="Selecciona una o más opciones",
    )
    st.session_state.seleccionadas = seleccionadas

if st.session_state.get("seleccionadas") and st.button("🔎 Buscar dominios"):
    seleccionadas = st.session_state.seleccionadas

    # Comprobar si el usuario tiene plan activo
    # Ya tienes `plan` arriba, no es necesario volver a pedirlo

    if plan == "free":
        try:
            # Precio por defecto del plan Básico
            price_id = os.getenv("STRIPE_PRICE_BASICO", "")
            if not price_id:
                st.error("Falta configurar el price_id del plan Básico.")
                st.stop()
            r_checkout = requests.post(
                f"{BACKEND_URL}/crear_checkout",
                headers=headers,
                params={"plan": price_id}
            )
            if r_checkout.ok:
                checkout_url = safe_json(r_checkout).get("url", "")
                st.warning("🚫 Tu suscripción actual no permite extraer leads.")
                subscription_cta()
                st.markdown(f"""
                <div style='text-align:center; margin-top: 1rem;'>
                    <a href="{checkout_url}" target="_blank" style='
                        background-color: #0d6efd;
                        color: white;
                        padding: 0.6rem 1.4rem;
                        border-radius: 6px;
                        text-decoration: none;
                        font-weight: 600;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        display: inline-block;
                        transition: background-color 0.3s ease;'>
                        💳 Suscribirme ahora
                    </a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("🚫 Tu suscripción no permite extraer leads. Suscríbete para usar esta función.")
                subscription_cta()
        except Exception:
            st.warning("🚫 Tu suscripción no permite extraer leads. Suscríbete para usar esta función.")
            subscription_cta()
    else:
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
        st.dataframe(st.session_state.resultados)

    # Limpiar flags para futuras búsquedas
    for flag in [
        "fase_extraccion",
        "guardando_mostrado",
        "mostrar_resultado",
        "export_realizado",
        "export_exitoso",
        "extraccion_realizada",
    ]:
        st.session_state.pop(flag, None)
