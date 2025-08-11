import os
import streamlit as st
from dotenv import load_dotenv

from session_bootstrap import bootstrap
bootstrap()

from cache_utils import cached_get, get_openai_client
from plan_utils import obtener_plan, tiene_suscripcion_activa, subscription_cta
from auth_utils import ensure_token_and_user, logout_button

st.set_page_config(page_title="Asistente Virtual", page_icon="🤖")  # ✅ PRIMERO
logout_button()
ensure_token_and_user()

# ────────────────── Config ──────────────────────────
load_dotenv()


def _safe_secret(name: str, default=None):
    """Safely retrieve configuration from env or Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


BACKEND_URL = _safe_secret("BACKEND_URL", "https://opensells.onrender.com")
client = get_openai_client()

st.title("🤖 Tu Asistente Virtual")

if "token" not in st.session_state:
    st.error("Debes iniciar sesión para usar el asistente.")
    st.stop()

plan = obtener_plan(st.session_state.token)


# ────────────────── Datos base ──────────────────────
nichos = cached_get("mis_nichos", st.session_state.token).get("nichos", [])
tareas = cached_get("tareas_pendientes", st.session_state.token).get("tareas", [])

resumen_nichos = ", ".join(n["nicho_original"] for n in nichos) or "ninguno"
resumen_tareas = f"Tienes {len(tareas)} tareas pendientes."

# ────────────────── Conversación ────────────────────
if "chat" not in st.session_state:
    st.session_state.chat = []

for entrada in st.session_state.chat:
    with st.chat_message(entrada["role"]):
        st.markdown(entrada["content"])

pregunta = st.chat_input("Haz una pregunta sobre tus nichos, leads o tareas...")

if pregunta:
    if not tiene_suscripcion_activa(plan):
        st.warning("Esta funcionalidad está disponible solo para usuarios con suscripción activa.")
        subscription_cta()
    else:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        contexto = f"""
Eres un asistente que ayuda a un usuario a consultar su base de datos de leads.
El usuario tiene estos nichos: {resumen_nichos}.
Resumen de tareas: {resumen_tareas}.

Responde de forma clara, breve y específica. Si no puedes responder con la información dada, pide más detalles.
"""

        messages = [
            {"role": "system", "content": contexto},
            *st.session_state.chat[-5:]
        ]

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.4
            )
            content = response.choices[0].message.content
        except Exception as e:
            content = f"Lo siento, ha ocurrido un error: {e}"

        st.session_state.chat.append({"role": "assistant", "content": content})
        with st.chat_message("assistant"):
            st.markdown(content)
