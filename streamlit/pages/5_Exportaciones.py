import streamlit as st
from session_bootstrap import bootstrap
from auth_utils import ensure_token_and_user, logout_button
from utils import http_client

bootstrap()

st.set_page_config(page_title="Exportaciones", page_icon="📤")


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

logout_button()

st.title("📤 Exportaciones")
st.info("Esta sección estará disponible pronto.")
