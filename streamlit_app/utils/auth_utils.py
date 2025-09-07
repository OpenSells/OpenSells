import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _save_session(token: str):
    st.session_state["jwt"] = token


def get_session():
    return st.session_state.get("jwt")


def logout():
    st.session_state.pop("jwt", None)
    st.rerun()


def login_with_email(email: str, password: str):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            if token:
                _save_session(token)
                return True, ""
        return False, resp.json().get("detail", "Credenciales inválidas.")
    except Exception as e:
        return False, str(e)


def register_user(username: str, email: str, password: str):
    try:
        payload = {"username": username, "email": email, "password": password}
        resp = requests.post(f"{BACKEND_URL}/register", json=payload, timeout=20)
        if resp.status_code == 201:
            return True, ""
        return False, resp.json().get("detail", "No se pudo registrar.")
    except Exception as e:
        return False, str(e)


def get_profile():
    token = get_session()
    if not token:
        return None
    try:
        resp = requests.get(
            f"{BACKEND_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None
