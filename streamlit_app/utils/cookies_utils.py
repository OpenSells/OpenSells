import streamlit as st
import extra_streamlit_components as stx
from typing import Optional


def _get_cookie_manager() -> stx.CookieManager:
    # Debe existir un único CookieManager "montado" en el árbol de la app
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager


def init_cookie_manager_mount() -> None:
    """Debe llamarse al inicio de la app para montar el CookieManager."""
    _get_cookie_manager()


def set_auth_token(token: str, days: int = 7) -> None:
    if not token:
        return
    cm = _get_cookie_manager()
    max_age = days * 24 * 3600
    try:
        cm.set(
            "wrapper_token",
            str(token),
            max_age=max_age,
            path="/",
            secure=True,
            same_site="Lax",
        )
    except Exception:
        # No romper la app si el navegador bloquea cookies
        pass


def get_auth_token() -> Optional[str]:
    cm = _get_cookie_manager()
    try:
        return cm.get("wrapper_token") or None
    except Exception:
        return None


def clear_auth_token() -> None:
    cm = _get_cookie_manager()
    try:
        cm.delete("wrapper_token", path="/")
    except Exception:
        pass


# Backwards compatibility helpers ----------------------------------------

def set_auth_cookies(token: str, email: Optional[str] = None, days: int = 7) -> None:
    """Deprecated wrapper maintained for older imports."""
    set_auth_token(token, days=days)


def clear_auth_cookies() -> None:
    """Deprecated wrapper maintained for older imports."""
    clear_auth_token()
