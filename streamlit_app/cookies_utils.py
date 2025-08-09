import extra_streamlit_components as stx
from datetime import datetime, timedelta
import streamlit as st


def get_cm():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager


def set_auth_cookies(token, email, days=7):
    cm = get_cm()
    expires = (datetime.utcnow() + timedelta(days=days)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    cm.set("wrapper_token", token, expires=expires, path="/")
    if email:
        cm.set("wrapper_email", email, expires=expires, path="/")


def clear_auth_cookies():
    cm = get_cm()
    cm.delete("wrapper_token", path="/")
    cm.delete("wrapper_email", path="/")
