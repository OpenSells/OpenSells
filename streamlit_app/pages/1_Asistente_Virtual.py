import time
import streamlit as st

from streamlit_app.utils.auth_utils import ensure_session, logout_and_redirect
from streamlit_app.utils import http_client

st.set_page_config(page_title="Asistente Virtual", page_icon="🤖")

user, token = ensure_session(require_auth=True)

if st.sidebar.button("Cerrar sesión"):
    logout_and_redirect()


def _auth_headers():
    return {"Authorization": f"Bearer {token}"} if token else {}


if "request_id" not in st.session_state:
    st.session_state.request_id = None
if "search_busy" not in st.session_state:
    st.session_state.search_busy = False

st.title("🤖 Asistente Virtual")

# Paso 1: Nicho
usar_existente = st.radio(
    "Nicho",
    ["Usar nicho existente", "Crear nicho nuevo"],
    disabled=st.session_state.search_busy,
)
usar_nicho_existente = usar_existente == "Usar nicho existente"

nicho = ""
if usar_nicho_existente:
    nichos = []
    if not st.session_state.search_busy:
        r = http_client.get("/mis_nichos", headers=_auth_headers())
        if r.status_code == 200:
            nichos = [n.get("nicho_original") or n["nicho"] for n in r.json().get("nichos", [])]
    nicho = st.selectbox("Selecciona nicho", nichos)
else:
    nicho = st.text_input("Nombre del nicho")

geo = st.text_input("Ubicación/Geo", disabled=st.session_state.search_busy)
palabras = st.text_input("Palabras clave (opcional)", disabled=st.session_state.search_busy)

if st.button("Generar sugerencias", disabled=st.session_state.search_busy or not nicho or not geo):
    payload = {
        "nicho": nicho,
        "usar_nicho_existente": usar_nicho_existente,
        "geo": geo,
        "palabras_clave": palabras or None,
    }
    r = http_client.post("/asistente/preparar", json=payload, headers=_auth_headers())
    if r.status_code == 200:
        data = r.json()
        st.session_state.sugeridas = data.get("variantes_sugeridas", [])
    else:
        st.error("No se pudieron generar sugerencias")

variantes_elegidas = []
if "sugeridas" in st.session_state:
    st.subheader("Variantes sugeridas")
    variantes_elegidas = st.multiselect(
        "Elige variantes",
        st.session_state.sugeridas,
        default=st.session_state.sugeridas,
    )
    nueva = st.text_input("Añadir variante personalizada", key="var_custom")
    if st.button("Agregar variante"):
        if nueva:
            st.session_state.sugeridas.append(nueva)
            st.session_state.sugeridas = list(dict.fromkeys(st.session_state.sugeridas))
            variantes_elegidas.append(nueva)
    st.info(
        "Se extraerán como máximo 10 leads por variante. Cuantas más variantes elijas, más tardará."
    )

    if st.button(
        "Iniciar extracción",
        disabled=st.session_state.search_busy or not variantes_elegidas,
    ):
        payload = {
            "nicho": nicho,
            "usar_nicho_existente": usar_nicho_existente,
            "geo": geo,
            "variantes_elegidas": variantes_elegidas,
            "palabras_clave": palabras or None,
        }
        r = http_client.post("/asistente/confirmar", json=payload, headers=_auth_headers())
        if r.status_code == 200:
            resp = r.json()
            st.session_state.request_id = resp.get("request_id")
            st.session_state.search_busy = True
            if resp.get("status") == "duplicate_ignored":
                st.info("Extracción ya en curso, reanudando...")
        else:
            st.error("Error al iniciar extracción")

if st.session_state.search_busy and st.session_state.request_id:
    st.info("Extrayendo leads… Puede tardar unos minutos; todo va bien ✅")
    status_box = st.empty()
    progress = st.progress(0)

    while st.session_state.search_busy:
        r = http_client.get(
            "/asistente/estado",
            headers=_auth_headers(),
            params={"request_id": st.session_state.request_id},
        )
        if r.status_code == 200:
            estado = r.json()
            total = estado.get("total_variantes", 1) * estado.get("total_paginas", 1)
            current = (
                (estado.get("variante_idx", 0) - 1) * estado.get("total_paginas", 1)
                + estado.get("pagina_idx", 0)
            )
            progress.progress(min(current / total, 1.0))
            status_box.write(
                f"Variante {estado.get('variante_idx')}/{estado.get('total_variantes')} - "
                f"Página {estado.get('pagina_idx')}/{estado.get('total_paginas')} - "
                f"Leads crudos: {estado.get('leads_crudos')} - Dominios únicos: {estado.get('dominios_unicos')}"
            )
            if estado.get("done"):
                st.session_state.search_busy = False
                st.success("Extracción finalizada")
                break
        else:
            status_box.write("Error obteniendo estado")
            break
        time.sleep(1)

    st.button("Ver leads del nicho")
