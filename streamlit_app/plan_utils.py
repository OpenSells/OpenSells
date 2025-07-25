import time
import streamlit as st
from cache_utils import cached_get


def obtener_plan(token: str) -> str:
    """Devuelve el plan actual del usuario o 'free' si no se puede determinar."""
    try:
        data = cached_get("protegido", token, nocache_key=time.time())
        if data:
            return (data.get("plan") or "free").strip().lower()
    except Exception:
        pass
    return "free"


def tiene_suscripcion_activa(plan: str) -> bool:
    """Indica si el plan permite funciones avanzadas."""
    return plan != "free"

