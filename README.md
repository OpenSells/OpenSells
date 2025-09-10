# OpenSells

*Actualizado el 10/09/2025*

**OpenSells** es un SaaS para generación y gestión de leads apoyado en un backend FastAPI y una interfaz multipágina en Streamlit.
Integra autenticación JWT, multitenencia mediante `user_email_lower` y planes de suscripción con límites de uso.

## 🆕 Novedades recientes

- **Memoria del asistente en PostgreSQL:** las interacciones se persisten y se incluye el script `scripts/migrar_memoria_sqlite_a_postgres.py` para migrar datos previos.
- **Extracción de leads desde el asistente deshabilitada:** guard de seguridad que impide usos no deseados.
- **Login y registro unificados en Home:** formulario combinado con botones de ancho completo.
- **Persistencia de sesión y cierre por inactividad:** los JWT se guardan en `localStorage` y expiran tras 20 min sin actividad.
- **Control de acceso uniforme:** todas las páginas excepto Home verifican sesión y muestran enlace a Home si el usuario no ha iniciado sesión.
- **Página “Búsqueda” mejorada:** expander con sugerencias de nichos y consejos, selector de nicho seguro y badge de plan en la barra lateral.
- **Página “Emails” (placeholder):** muestra "Disponible próximamente" con vista previa de envío 1:1, masivo y plantillas.
- **Aviso discreto de leads duplicados:** se reemplazó el warning por una nota sutil.
- **Gestión de sesión y rutas unificada:** refactor para centralizar manejo de tokens y paths en toda la app.
- **Clave multi‑tenant unificada:** todos los datos se filtran por `user_email_lower`; se añadió `/debug-user-snapshot` para diagnosticar sesión y base de datos.
- **Esquema multi‑tenant armonizado:** las tablas incluyen `user_email_lower` no nulo, índices compuestos y conteo de leads por dominio distinto vía `/conteo_leads`.
- **Validación de `DATABASE_URL`:** el backend avisa al arrancar si apunta a SQLite o falta la variable.
- **Migración a emails en minúsculas:** script `backend/scripts/migrate_emails_lowercase.py` para poblar e indexar campos `user_email_lower`.
- **Bloqueo de cuentas suspendidas:** columna `suspendido` en `usuarios` y guardias en login y webhook de Stripe para desactivar accesos.
- **Matriz de planes centralizada:** `backend/core/plans.py` y `backend/core/usage.py` definen límites y registran consumo mensual.

## 📊 Estado del proyecto

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL; endpoints para usuarios, nichos, leads, tareas, exportaciones y suscripciones (Stripe).
- **Frontend:** Streamlit multipágina con generación de leads, nichos, tareas, asistente virtual, exportaciones y control de acceso por plan.
- **Autenticación:** JWT persistido en cookies, helper `utils/auth_utils.py` para restaurar sesión y auto‑logout, y soporte para suspender cuentas mediante la columna `suspendido`.
- **Multi‑tenant:** clave `user_email_lower` en todas las tablas; endpoint `/debug-user-snapshot` para verificar sesión y prefijo de la base de datos.
- **Memoria del asistente:** conversaciones almacenadas en PostgreSQL con soporte de migración desde SQLite.
- **Control de uso:** `backend/core/usage.py` registra leads, mensajes de IA, tareas y exportaciones por mes.
- **Pruebas:** `pytest` cubre el backend y funcionalidades clave.

## 📁 Estructura del repositorio

- `backend/`: API FastAPI, modelos, dependencias y scripts de arranque. Incluye webhook de Stripe y scripts de migración.
- `streamlit_app/`: interfaz multipágina de Streamlit con utilidades comunes (`cache_utils`, `plan_utils`, etc.).
- `scraper/`: módulo `extractor.py` para extraer emails, teléfonos y redes sociales desde una URL.
- `scripts/`: herramientas adicionales como la migración de memoria a PostgreSQL.
- `backend/scripts/`: utilidades de migración de datos (p. ej. `migrate_emails_lowercase.py`).
- `utils/`: utilidades compartidas como `navegacion.py`.
- `tests/`: batería de pruebas con `pytest`.
- Otros archivos: `render.yaml` para despliegue, `runtime.txt`, carpeta `.devcontainer` para desarrollo y scripts `.bat` para Windows.

## 💻 Requisitos previos

- Python 3.11.8 (ver `runtime.txt`)
- pip

## 🛠️ Ejecución local

1. Instala dependencias y herramientas de migración:

```bash
pip install -r requirements.txt
alembic upgrade head
```

2. Inicia el backend:

```bash
uvicorn backend.main:app --reload
```

3. Inicia el frontend desde la raíz del proyecto:

```bash
streamlit run streamlit_app/Home.py
```

También puedes usar `backend/start.sh` o los scripts `.bat` en Windows.

## 🔑 Variables de entorno

Copia `.env.example` a `.env` y completa las claves necesarias (PostgreSQL, Stripe, etc.):

```bash
cp .env.example .env
```

Variables disponibles:

- `OPENAI_API_KEY`: clave para las llamadas a OpenAI y el scraper de contactos.
- `DATABASE_URL`: cadena de conexión a PostgreSQL.
- `SCRAPERAPI_KEY`: API key opcional para usar ScraperAPI.
- `STRIPE_PRICE_GRATIS`, `STRIPE_PRICE_BASICO`, `STRIPE_PRICE_PREMIUM`: identificadores de precios para los planes de Stripe.

El mapeo de estos `price_id` al nombre interno del plan se define en `backend/core/stripe_mapping.py`. El webhook de Stripe actualiza `usuario.plan` y asigna **free** si recibe un `price_id` desconocido.

## 📦 Planes y límites

La matriz de planes se centraliza en `backend/core/plans.py` y expone límites como `leads_mensuales`, `ia_mensajes`, `tareas_max`, `permite_notas` y `csv_exportacion`. El uso mensual se gestiona en `backend/core/usage.py` y el endpoint `GET /mi_plan` devuelve el plan y sus límites, consumidos en el frontend mediante `resolve_user_plan`.

## 🕷️ Scraper de contactos

El script `scraper/extractor.py` utiliza `requests`, `BeautifulSoup`, `phonenumbers` y la API de OpenAI para analizar una página web y devolver los mejores emails, teléfonos y enlaces sociales detectados.

```python
from scraper.extractor import extraer_datos_desde_url
extraer_datos_desde_url("https://example.com")
```

## 🚢 Despliegue

El archivo `render.yaml` describe un servicio web para desplegar el backend en [Render](https://render.com/). El comando de inicio por defecto es `uvicorn backend.main:app --host 0.0.0.0 --port 10000`.

## 🧪 Pruebas

```bash
python -m py_compile $(git ls-files '*.py')
pytest
```

## 🚀 Próximos pasos

- Configurar autenticación en el entorno de pruebas para que `pytest` se ejecute correctamente.
- Añadir envío de emails real en la página *Emails*.
- Mejorar estilo global (tipografía, botones) y paginación/ordenación de tablas de leads.
- Guardar la última página visitada para restaurarla tras login o refresh.

OpenSells sigue evolucionando hacia un servicio estable de generación de leads con modelo freemium.

**👨‍💻 Ayrton**

*(Generado automáticamente el 10/09/2025.)*

