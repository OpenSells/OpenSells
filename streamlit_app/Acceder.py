import streamlit as st
from utils.http_client import post
from utils.auth_session import set_auth_token, get_auth_token

PAGE_MAP = {
    "Leads": "pages/1_Busqueda.py",
    "Tareas": "pages/4_Tareas.py",
    "Nichos": "pages/3_Mis_Nichos.py",
    "Asistente": "pages/2_Asistente_Virtual.py",
    "Exportaciones": "pages/5_Exportaciones.py",
    "Emails": "pages/6_Emails.py",
    "Suscripcion": "pages/7_Suscripcion.py",
    "Cuenta": "pages/8_Mi_Cuenta.py",
    "Home": "Home.py",
}


def _redirect_after_login():
    page_name = st.query_params.get("p", "Leads")
    page_file = PAGE_MAP.get(page_name, "pages/1_Busqueda.py")
    st.switch_page(page_file)


def main():
    token = get_auth_token()
    if token:
        _redirect_after_login()
        st.stop()

    st.title("Acceder")
    with st.form("login"):
        user = st.text_input("Usuario o email")
        pwd = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            resp = post("/login", json={"username": user, "password": pwd})
            if isinstance(resp, dict) and resp.get("_error"):
                st.error("No autorizado.")
                return
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            if not token:
                st.error("Respuesta de login inválida.")
                return
            set_auth_token(token)
            st.success("Sesión iniciada.")
            st.rerun()


if __name__ == "__main__":
    main()
