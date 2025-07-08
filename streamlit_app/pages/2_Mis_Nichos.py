# 2_Mis_Nichos.py – Página de gestión de nichos y leads
#
# ✔️  Correcciones principales
#   1. El buscador global solo está visible cuando se muestran **todos** los nichos,
#      así evitamos que el usuario lo confunda con el filtro interno.
#   2. La vista de “solo nicho” se mantiene tras:
#        • borrar un lead
#        • usar el filtro interno de ese nicho
#      (solo desaparece al pulsar “Volver a todos los nichos” o al borrar el nicho completo).
#   3. Eliminado el bloque duplicado de `st.experimental_rerun()` que provocaba
#      reruns innecesarios.
#   4. Limpieza y tipado ligero.

import os
import hashlib
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv

# ── Config ───────────────────────────────────────────
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://opensells.onrender.com")
st.set_page_config(page_title="Mis Nichos", page_icon="📁")

# ── Helpers ──────────────────────────────────────────
def h() -> dict:
    """Cabeceras con el JWT."""
    return {"Authorization": f"Bearer {st.session_state.token}"}

def normalizar_dominio(url: str) -> str:
    if not url:
        return ""
    url = url if url.startswith(("http://", "https://")) else f"http://{url}"
    return urlparse(url).netloc.replace("www.", "").split("/")[0]

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

# ── Protección de acceso ─────────────────────────────
if "token" not in st.session_state:
    st.error("Debes iniciar sesión para ver esta página.")
    st.stop()

# ── Título ───────────────────────────────────────────
st.title("📁 Gestión de Nichos")

# ── Búsqueda global (solo en vista “todos los nichos”) ─────────────
if "solo_nicho_visible" not in st.session_state:
    busqueda = st.text_input(
        "🔍 Buscar nichos o leads:",
        value=st.session_state.get("busqueda_global", ""),
        key="input_busqueda_global",
    ).lower().strip()
else:
    # Cuando estamos en vista de un solo nicho no usamos el buscador global
    busqueda = ""

# ── Cargar nichos del backend ───────────────────────
resp = requests.get(f"{BACKEND_URL}/mis_nichos", headers=h())
nichos: list[dict] = resp.json().get("nichos", []) if resp.status_code == 200 else []

if not nichos:
    st.info("Aún no tienes nichos guardados.")
    st.stop()

# ── Construir índice rápido de leads (para búsquedas globales) ────
todos_leads = []
for n in nichos:
    r = requests.get(
        f"{BACKEND_URL}/leads_por_nicho",
        params={"nicho": n["nicho"]},
        headers=h(),
    )
    leads = r.json().get("leads", []) if r.status_code == 200 else []
    n["total_leads"] = len(leads)

    for idx, l in enumerate(leads):
        d = normalizar_dominio(l["url"])
        todos_leads.append(
            {
                "dominio": d,
                "nicho": n["nicho"],
                "nicho_original": n["nicho_original"],
                "key": md5(f"{d}_{idx}"),
            }
        )

# ── Resultados del buscador global ──────────────────
if busqueda:
    st.session_state["busqueda_global"] = busqueda
    st.markdown("---")
    st.subheader("🔎 Resultados de búsqueda")

    leads_coinc = [l for l in todos_leads if busqueda in l["dominio"]]
    nichos_coinc = [n for n in nichos if busqueda in n["nicho_original"].lower()]

    # Leads coincidentes
    for idx, l in enumerate(leads_coinc):
        if st.button(
            f"🌐 {l['dominio']} → {l['nicho_original']}",
            key=f"lead_{l['key']}_{idx}",
        ):
            st.session_state["solo_nicho_visible"] = l["nicho"]
            st.session_state["busqueda_global"] = ""
            st.experimental_rerun()

    # Nichos coincidentes (solo listamos, sin interacción de momento)
    for n in nichos_coinc:
        st.markdown(f"📂 {n['nicho_original']}")

    st.stop()  # solo mostramos resultados, no renderizamos nada más

# ── Botón «Volver a todos los nichos» ───────────────
if "solo_nicho_visible" in st.session_state:
    if st.button("🔙 Volver a todos los nichos", key="volver_todos"):
        st.session_state.pop("solo_nicho_visible")
        st.session_state.pop("busqueda_global", None)
        st.experimental_rerun()

# ── Definir qué nichos se muestran ──────────────────
if "solo_nicho_visible" in st.session_state:
    nichos_visibles = [
        n for n in nichos if n["nicho"] == st.session_state["solo_nicho_visible"]
    ]
else:
    nichos_visibles = nichos

# ── Render de nichos y leads ────────────────────────
for n in nichos_visibles:
    key_exp = f"expandir_{n['nicho']}"
    expanded_por_defecto = "solo_nicho_visible" in st.session_state
    expanded = st.session_state.get(key_exp, expanded_por_defecto)

    with st.expander(
        f"📂 {n['nicho_original']} ({n['total_leads']} leads)",
        expanded=expanded,
    ):
        cols = st.columns([1, 1])

        # ── Descargar CSV ───────────────────────────
        ruta_csv = f"exports/{st.session_state.email}/{n['nicho']}.csv"
        if os.path.exists(ruta_csv):
            with open(ruta_csv, "rb") as f:
                cols[0].download_button(
                    "📥 Descargar CSV",
                    f.read(),
                    file_name=f"{n['nicho_original']}.csv",
                    mime="text/csv",
                    key=f"csv_{n['nicho']}",
                )

        # ── Eliminar nicho ──────────────────────────
        if cols[1].button("🗑️ Eliminar nicho", key=f"del_nicho_{n['nicho']}"):
            requests.delete(
                f"{BACKEND_URL}/eliminar_nicho",
                params={"nicho": n["nicho"]},
                headers=h(),
            )
            if st.session_state.get("solo_nicho_visible") == n["nicho"]:
                st.session_state.pop("solo_nicho_visible", None)
            st.experimental_rerun()

        # ── Cargar leads del nicho ───────────────────
        resp_leads = requests.get(
            f"{BACKEND_URL}/leads_por_nicho",
            params={"nicho": n["nicho"]},
            headers=h(),
        )
        leads = resp_leads.json().get("leads", []) if resp_leads.status_code == 200 else []

        # ── Filtro interno por dominio ───────────────
        filtro = st.text_input(
            "Filtrar leads por dominio:",
            key=f"filtro_{n['nicho']}",
            placeholder="Ej. clinicadental.com",
        ).lower().strip()

        if filtro:
            leads = [
                l for l in leads
                if filtro in normalizar_dominio(l["url"]).lower()
            ]

        st.markdown(f"### Total mostrados: {len(leads)}")

        # ── Añadir lead manual (compacto con toggle) ───────────────
        mostrar_form = st.toggle("➕ Añadir Lead Manualmente", key=f"toggle_lead_{n['nicho']}")
        if mostrar_form:
            with st.form(key=f"form_lead_manual_{n['nicho']}"):
                c1, c2 = st.columns(2)
                dominio_manual = c1.text_input("🌐 Dominio", key=f"dom_{n['nicho']}")
                email_manual = c2.text_input("📧 Email", key=f"email_{n['nicho']}")
                telefono_manual = c1.text_input("📞 Teléfono", key=f"tel_{n['nicho']}")
                nombre_manual = c2.text_input("🏷️ Nombre", key=f"nombre_{n['nicho']}")

                submitted = st.form_submit_button("✅ Añadir")

                if submitted:
                    if not dominio_manual:
                        st.warning("Debes introducir al menos el dominio.")
                    else:
                        dominio_normalizado = normalizar_dominio(dominio_manual)
                        dominios_existentes = {l["dominio"] for l in todos_leads}

                        if dominio_normalizado in dominios_existentes:
                            st.error("❌ Este dominio ya existe en tus leads.")
                        else:
                            res = requests.post(
                                f"{BACKEND_URL}/añadir_lead_manual",
                                headers=h(),
                                json={
                                    "dominio": dominio_manual,
                                    "email": email_manual,
                                    "telefono": telefono_manual,
                                    "nombre": nombre_manual,
                                    "nicho": n["nicho_original"]
                                }
                            )
                            if res.status_code == 200:
                                st.success("Lead añadido correctamente ✅")
                                st.session_state["solo_nicho_visible"] = n["nicho"]
                                st.session_state[key_exp] = True
                                st.rerun()
                            else:
                                st.error(f"Error al guardar: {res.json().get('detail', 'Error desconocido')}")

        if "lead_a_mover" not in st.session_state:
            st.session_state["lead_a_mover"] = None

        for i, l in enumerate(leads):
            dominio = normalizar_dominio(l["url"])
            clave_base = f"{dominio}_{n['nicho']}_{i}".replace(".", "_")
            cols_row = st.columns([4, 1, 1, 1])
            cols_row[0].markdown(f"- 🌐 [**{dominio}**](https://{dominio})", unsafe_allow_html=True)

            # Botón eliminar
            if cols_row[1].button("🗑️", key=f"btn_borrar_{clave_base}"):
                requests.delete(
                    f"{BACKEND_URL}/eliminar_lead",
                    params={
                        "nicho": n["nicho"],
                        "dominio": dominio,
                        "solo_de_este_nicho": "true",
                    },
                    headers=h(),
                )
                st.session_state[key_exp] = True
                st.session_state["solo_nicho_visible"] = n["nicho"]
                st.experimental_rerun()

                        # Botón Mover compacto
            if cols_row[2].button("🔀", key=f"btn_mostrar_mover_{clave_base}"):
                st.session_state["lead_a_mover"] = clave_base

            # Formulario de mover lead si está activo
            if st.session_state.get("lead_a_mover") == clave_base:
                nichos_destino = [ni["nicho_original"] for ni in nichos if ni["nicho"] != n["nicho"]]
                nuevo_nicho = st.selectbox("Mover a:", nichos_destino, key=f"select_nuevo_nicho_{clave_base}")

                if st.button("✅ Confirmar", key=f"confirmar_mover_{clave_base}"):
                    res = requests.post(
                        f"{BACKEND_URL}/mover_lead",
                        headers=h(),
                        json={
                            "dominio": dominio,
                            "origen": n["nicho_original"],
                            "destino": nuevo_nicho
                        }
                    )
                    if res.status_code == 200:
                        st.success("Lead movido correctamente ✅")
                        st.session_state["lead_a_mover"] = None
                        st.session_state["solo_nicho_visible"] = n["nicho"]
                        st.rerun()
                    else:
                        st.error(f"Error al mover lead: {res.json().get('detail', 'Error desconocido')}")

            # Botón Información extra
            if cols_row[3].button("📝", key=f"btn_info_{clave_base}"):
                st.session_state[f"mostrar_info_{clave_base}"] = not st.session_state.get(f"mostrar_info_{clave_base}", False)

            # Formulario de info extra si está activado
            if st.session_state.get(f"mostrar_info_{clave_base}", False):
                info = requests.get(
                    f"{BACKEND_URL}/info_extra",
                    params={"dominio": dominio},
                    headers=h()
                ).json()

                with st.form(key=f"form_info_extra_{clave_base}"):
                    c1, c2 = st.columns(2)
                    email_nuevo = c1.text_input("📧 Email", value=info.get("email_contacto", ""), key=f"email_{clave_base}")
                    tel_nuevo = c2.text_input("📞 Teléfono", value=info.get("telefono", ""), key=f"tel_{clave_base}")
                    info_nueva = st.text_area("📝 Información libre", value=info.get("info_adicional", ""), key=f"info_{clave_base}")

                    if st.form_submit_button("💾 Guardar información"):
                        res = requests.post(
                            f"{BACKEND_URL}/guardar_info_extra",
                            headers=h(),
                            json={
                                "dominio": dominio,
                                "email_contacto": email_nuevo,
                                "telefono": tel_nuevo,
                                "info_adicional": info_nueva
                            }
                        )
                        if res.status_code == 200:
                            st.success("Información guardada correctamente ✅")
