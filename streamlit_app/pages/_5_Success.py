import streamlit as st

st.set_page_config(page_title="✅ Suscripción completada", layout="centered", initial_sidebar_state="collapsed")

st.title("✅ ¡Suscripción completada!")
st.success("Tu plan ha sido activado correctamente.")
st.markdown("Puedes volver a la sección de búsqueda o nichos para empezar a usar la plataforma.")
st.page_link("1_Busqueda", label="🔍 Ir a Búsqueda")
