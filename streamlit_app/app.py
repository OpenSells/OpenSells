import streamlit as st
import requests
import pandas as pd

# URL pública de tu backend en Render
API_URL = "https://wrapper-leads-saas.onrender.com"

st.set_page_config(page_title="Lead Wrapper", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f7f9fa; }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #2c3e50;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Wrapper de Leads por Nicho")
st.markdown("Encuentra y extrae datos de clientes potenciales en segundos.")

st.divider()

# === BLOQUE 1: BÚSQUEDA ===
st.header("1️⃣ Buscar cliente ideal")

cliente_ideal = st.text_input("Describe tu cliente ideal (ej: agencias de marketing en España)")

if st.button("🔍 Generar búsqueda"):
    with st.spinner("Buscando URLs en Google..."):
        r = requests.post(f"{API_URL}/buscar", json={"cliente_ideal": cliente_ideal})
        if r.status_code == 200:
            data = r.json()
            st.session_state["urls_obtenidas"] = data.get("urls_obtenidas", [])
            st.session_state["payload_listo"] = data.get("payload_listo", {})
            st.success("¡URLs encontradas!")
        else:
            st.error("❌ Error al generar búsqueda")

# === BLOQUE 2: SELECCIÓN DE URLS ===
if "urls_obtenidas" in st.session_state:
    st.header("2️⃣ Selecciona URLs para extraer leads")

    urls_seleccionadas = st.multiselect("URLs encontradas:", st.session_state["urls_obtenidas"])

    if urls_seleccionadas and st.button("📤 Extraer datos de esas URLs"):
        with st.spinner("Extrayendo datos..."):
            payload = {
                "urls": urls_seleccionadas,
                "pais": "ES"
            }
            r = requests.post(f"{API_URL}/extraer_multiples", json=payload)
            if r.status_code == 200:
                resultados = r.json()
                df = pd.DataFrame(resultados)
                st.session_state["df_resultado"] = df
                st.success("¡Datos extraídos correctamente!")
            else:
                st.error("❌ Error al extraer datos")

# === BLOQUE 3: RESULTADOS ===
if "df_resultado" in st.session_state:
    st.header("3️⃣ Leads extraídos")
    st.dataframe(st.session_state["df_resultado"])

    if st.button("📥 Exportar a CSV"):
        r = requests.post(f"{API_URL}/exportar_csv", json={
            "urls": st.session_state["df_resultado"]["url"].tolist(),
            "pais": "ES"
        })
        if r.status_code == 200:
            st.success("Archivo CSV generado correctamente (descárgalo desde el backend o Swagger).")
        else:
            st.error("❌ Error al exportar CSV")
