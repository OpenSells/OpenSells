# Wrapper Leads SaaS 🚀

Wrapper Leads SaaS es una plataforma SaaS para la extracción automática de leads desde sitios web públicos, combinando scraping inteligente, procesamiento IA y una interfaz sencilla.

---

## 🧠 Objetivo del Proyecto
- Generar leads B2B y B2C desde dominios públicos.
- Enriquecer resultados automáticamente con OpenAI.
- Permitir uso sin conocimientos técnicos.
- Evolucionar a modelo freemium con alta facilidad de uso.
- Sugerir nuevos nichos basados en memoria del usuario y actividad previa.

---

## 🚀 Tecnologías Usadas
- **FastAPI** para backend (API REST).
- **Uvicorn** como servidor ASGI.
- **ScraperAPI + BeautifulSoup4** para scraping inteligente.
- **OpenAI API** (openai>=1.0.0) para generación de variantes y sugerencias.
- **Streamlit** para el frontend multipágina con control avanzado de estado.
- **SQLite** como base de datos en desarrollo.
- **dotenv** para gestión de variables sensibles.

---

## 📂 Estructura del Proyecto

```
wrapper-leads-saas/
├── backend/             # API FastAPI
├── scraper/             # Extracción inteligente
├── streamlit_app/       # Frontend visual en Streamlit
├── exports/             # CSVs generados por usuario/nicho
├── admin_data/          # CSV global de todos los leads
├── utils/               # Funciones auxiliares
├── tests/               # Tests automáticos
├── requirements.txt
├── iniciar.bat
└── README.md
```

---

## 🛠 Instalación Local (Windows)

```bash
git clone https://github.com/Ayrtonlink/wrapper-leads-saas.git
cd wrapper-leads-saas
call env\Scripts\activate.bat
pip install -r requirements.txt
uvicorn backend.main:app --reload
streamlit run streamlit_app/app.py
```

Crear `.env` con:

```ini
OPENAI_API_KEY=your_openai_key
SCRAPERAPI_KEY=your_scraperapi_key
SECRET_KEY=una_clave_segura
ENV=local
```

---

## ✅ Funcionalidades Principales

- 🔐 Registro y login de usuarios (JWT).
- 🧠 Generación de variantes de búsqueda con IA.
- 🌐 Extracción de leads basada en dominios limpios y normalizados.
- 📄 Exportación de leads a CSV por nicho y exportación global.
- 🗂️ Gestión avanzada de leads por estado (`nuevo`, `contactado`, `interesado`, `no responde`).
- 📝 Notas independientes por lead (sin mezcla entre leads ni usuarios).
- 🔍 Buscador global de leads por dominio, estado y notas.
- 📥 Importar leads desde archivos CSV estándar.
- 📜 Historial automático de acciones por lead.
- 📋 Gestión de tareas por lead, por nicho o generales.
- 🚦 Prioridad visual en tareas (alta, media, baja).
- 🧹 Limpieza automática del estado entre páginas.
- 🌟 Sugerencias inteligentes de nuevos nichos.
- 🧠 Popup visual bloqueante para procesos largos.
- 🔄 Automatización completa tras pulsar "Buscar dominios".
- 💬 Asistente virtual contextual con acceso a tus nichos y tareas.
- 📅 Notas y fechas personalizadas en tareas por lead/nicho/general.

---

## 🔥 Cambios Recientes (Actualización 02/06/2025)

- ✅ Integración del asistente virtual en Streamlit con OpenAI.
- ✅ Vista mejorada de tareas por tipo (general, nicho, lead).
- ✅ Gestión de prioridades y notas en tareas.
- ✅ Popup actualizado con paso dinámico visible.
- ✅ Cierre automático del popup al finalizar la extracción.
- ✅ Visualización del DataFrame + mensaje post-extracción.
- ✅ Sugerencias de nicho reactivadas y contextualizadas.
- ✅ Texto “Selecciona una opción” en español.
- ✅ Botón “Crear nuevo nicho” primero en el selector.
- ✅ Sin `st.rerun()` prematuros que oculten el resultado.

---


---

## 🆕 Cambios posteriores al 02/06/2025 (actualizado 16/06/2025)

- ✅ Endpoint `/tareas_pendientes` reestructurado para mayor limpieza (extraído a `db.py`).
- ✅ Filtrado visual de tareas completadas en la sección "Pendientes".
- ✅ Eliminado el uso de `...` (ellipsis) en edición de notas para evitar errores de serialización.
- ✅ Validación segura de prioridades en tareas (evita valores `None`).
- ✅ En `/tareas_lead` ahora se devuelve `tipo`, `prioridad` y `dominio` para visualización correcta.
- ✅ Corrección del ícono e información del lead asignado en tareas tipo `lead` (sección "Leads").



## 🆕 Cambios posteriores al 27/06/2025

- ✅ La extracción ahora solo guarda `Dominio` y `Fecha` por lead, sin emails, teléfonos ni redes sociales.
- ✅ Eliminado el enriquecimiento IA durante la extracción para mejorar velocidad y evitar errores innecesarios.
- ✅ Validación en backend para evitar guardar leads repetidos por dominio, sin importar el nicho.
- ✅ `/añadir_lead_manual` ahora también valida duplicados globales y guarda solo dominio + fecha.
- ✅ Se oculta el campo de refinamiento si la IA responde "OK." para evitar confusión en el flujo de búsqueda.


## 🆕 Cambios posteriores al 29/06/2025

- ✅ Eliminado el scraping web en `/extraer_multiples`. Ahora solo se procesa el dominio base sin llamadas a ScraperAPI ni a BeautifulSoup.
- ✅ Extracción mucho más rápida, sin costes ni retardo, ideal para grandes volúmenes.
- ✅ El backend ya no llama a `extraer_datos_desde_url`, ni siquiera internamente.
- ✅ Añadida la tabla `lead_info_extra` para permitir que cada usuario asocie a cada lead:
  - 📧 Email de contacto
  - 📞 Teléfono
  - 📝 Información adicional
- ✅ Nuevas funciones en `db.py`: `guardar_info_extra` y `obtener_info_extra`.
- ✅ Nuevos endpoints en FastAPI:
  - `POST /guardar_info_extra` para guardar info opcional.
  - `GET /info_extra?dominio=...` para recuperarla.
- ✅ El historial registra un evento tipo `"info"` cuando se actualiza esta información.
- ✅ En `3_Tareas.py`, al seleccionar un dominio, se muestra un formulario editable con estos campos debajo del historial y tareas.

## 🆕 Cambios posteriores al 30/06/2025

- ✅ Añadido campo `plan` al modelo de usuarios para definir suscripción activa o gratuita.
- ✅ Todos los nuevos registros se crean con `plan = "free"` por defecto.
- ✅ Nueva función `validar_suscripcion()` que bloquea endpoints clave para usuarios sin suscripción activa.
- ✅ Endpoints protegidos con validación de plan:
  - `/exportar_csv`
  - `/extraer_multiples`
  - `/extraer_datos`
  - `/añadir_lead_manual`
  - `/importar_csv_manual`
- ✅ Página “Mi Cuenta” ahora muestra el plan actual del usuario y avisa si está en modo gratuito.
- ✅ Integración con Stripe:
  - `POST /crear_checkout` para iniciar pago con plan.
  - `GET /portal_cliente` para gestionar suscripciones.
  - Selección de plan desde frontend con redirección automática a Stripe Checkout.
- ✅ Endpoint `/webhook` preparado para actualizar el plan del usuario cuando finaliza la compra.
- ⚠️ El webhook de Stripe queda pendiente de activar cuando se tenga dominio público (requisito de Stripe).

## 🆕 Cambios posteriores al 01/07/2025

- ✅ Validación visual en frontend para evitar que usuarios con plan `free` accedan a la extracción de leads.
- ✅ Al hacer clic en “Buscar dominios”, si el usuario no tiene suscripción, aparece un aviso con botón directo a Stripe.
- ✅ Enlace visual de pago dentro del mensaje: se abre Stripe Checkout automáticamente con `window.open(...)` en HTML.
- ✅ Mejoras en `4_Mi_Cuenta.py` para asegurar que la redirección a Stripe funcione sin errores desde Streamlit.
- ✅ Se añadió botón 📝 en la vista de “Mis Nichos” junto a los botones de mover y borrar para editar la info extra de cada lead.
- ✅ El formulario de info extra ahora se muestra al hacer clic sobre el botón correspondiente, de forma individual por lead.
- ✅ El nombre del dominio en “Mis Nichos” ahora es clicable y abre la web en una nueva pestaña.
- ✅ Lo mismo se aplica al dominio seleccionado en la sección “Leads” dentro de “Tareas”.

## 🆕 Cambios posteriores al 03/07/2025

- ✅ Rediseño visual completo de la sección de tareas en `3_Tareas.py`:
  - Las tareas generales, por lead y por nicho se dividen en dos fases: búsqueda/listado y vista individual.
  - Se usa botón “➡️ Ver” para abrir el detalle, y “⬅️ Volver” para regresar.
  - La vista individual incluye toggles para añadir tarea y ver historial, con diseño compacto y ordenado.

- ✅ Se añadió campo de búsqueda por nombre en la vista de nichos para facilitar el filtrado.

- ✅ Visualización mejorada de la columna de asignación de tareas:
  - Leads: 🌐 dominio.com
  - Nichos: 📂 nombre del nicho
  - Generales: 🧠 General
  - Se eliminan temporalmente los enlaces internos hasta mejorar su comportamiento.

- ✅ Correcciones:
  - Solucionado error visual con nombres de nichos en Markdown.
  - Eliminado `unsafe_allow_html=True` en la tabla de tareas.
  - Reemplazado `st.experimental_get_query_params()` por `st.query_params` + `clear()` según recomendación oficial.

## ❓ Pendientes Actuales

- ❌ Migrar CSVs antiguos a base de datos.
- 🔄 Añadir barra de progreso real durante extracción.
- ✨ Mejoras estéticas en el frontend (margen, estilo, colores).
- 🔁 Vincular sugerencias de nicho al input cliente ideal.
- 📎 Botón directo a “Mis Nichos” al finalizar proceso.
- 📨 Sistema de emails automáticos desde IA.
- 📂 Mover leads entre nichos con detección de duplicados.

---

## 🧪 Tests

```bash
pytest tests/
```

---

## 👤 Autor

- Ayrton  
- GitHub: [Ayrtonlink](https://github.com/Ayrtonlink)

## 🆕 Cambios posteriores al 27/06/2025

- ✅ Implementado sistema visual compacto para mover leads entre nichos desde el frontend.
- ✅ Botón 🔀 alineado horizontalmente con el dominio y el botón 🗑️, sin expanders ni popovers anidados.
- ✅ Eliminado el uso de `st.popover()` para evitar diferencias de altura visual.
- ✅ Se usa `st.session_state["lead_a_mover"]` para mostrar el selector solo tras hacer clic.
- ✅ Claves únicas garantizadas para cada botón y selectbox por lead.
- ✅ El botón de eliminar `❌` ha sido reemplazado por 🗑️ para mayor coherencia visual.
- ✅ Todo el manejo de leads ahora se realiza en una línea compacta por lead.

## 🆕 Cambios posteriores al 21/06/2025

- ✅ El historial de tareas generales y de nichos ahora funciona correctamente y por separado.
- ✅ El endpoint `/historial_tareas` acepta ahora un parámetro opcional `nicho` para filtrar correctamente.
- ✅ Se añadió la función `obtener_historial_por_nicho` en `db.py`.
- ✅ Se corrigió la función `obtener_historial_por_tipo` para que devuelva también el campo `tipo`.
- ✅ El backend guarda correctamente los eventos de tareas completadas por tipo `general`, `nicho` y `tarea` (leads).
- ✅ El frontend filtra correctamente los eventos que comienzan con `Tarea completada:`.
- ✅ Se eliminó por completo el sistema de notas por tarea (ya no se usan ni se guardan).
- ✅ El formulario de edición de tareas se rediseñó como bloque visible con botón ❌ de cierre inmediato.
