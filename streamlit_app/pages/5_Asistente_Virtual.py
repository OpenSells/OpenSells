import streamlit as st
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

# ────────────────── Config ──────────────────────────
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="Asistente Virtual", page_icon="🤖")
st.title("🤖 Tu Asistente Virtual")

if "token" not in st.session_state:
    st.error("Debes iniciar sesión para usar el asistente.")
    st.stop()

HDR = {"Authorization": f"Bearer {st.session_state.token}"}

# ────────────────── Helpers ─────────────────────────
def api_get(endpoint: str, **params):
    try:
        r = requests.get(f"{BACKEND_URL}/{endpoint}", params=params, headers=HDR, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ────────────────── Datos base ──────────────────────
nichos = api_get("mis_nichos").get("nichos", [])
tareas = api_get("tareas_pendientes").get("tareas", [])

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
        *st.session_state.chat[-5:]  # última parte del historial
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
