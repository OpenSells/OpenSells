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
- **Base de datos solo PostgreSQL:** se eliminó soporte a SQLite y se valida que `DATABASE_URL` no use ese motor.
- **Migración a emails en minúsculas:** script `backend/scripts/migrate_emails_lowercase.py` para poblar e indexar campos `user_email_lower`.
- **Matriz de planes centralizada:** `backend/core/plan_config.py` y `backend/core/usage.py` definen límites y registran consumo.
- **Suspensión de usuarios:** columna `suspendido` en `usuarios` y guard que bloquea acceso si está activa.
- **Depuración de tablas legado:** eliminadas referencias a `users` y `usage_counters`; la info de usuarios se gestiona solo en `usuarios` y el uso mensual en `user_usage_monthly`.

## 📊 Estado del proyecto

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL; endpoints para usuarios, nichos, leads, tareas, exportaciones y suscripciones (Stripe).
- **Frontend:** Streamlit multipágina con generación de leads, nichos, tareas, asistente virtual, exportaciones y control de acceso por plan.
- **Autenticación:** JWT persistido en cookies y helper `utils/auth_utils.py` para restaurar sesión y auto‑logout.
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

## 🔌 Endpoints principales

No existe prefijo global; todas las rutas se sirven desde la raíz del dominio.

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| POST | /register | Crear usuario |
| POST | /login | Obtener JWT |
| GET | /me | Usuario autenticado |
| GET | /mi_plan | Plan actual y límites |
| GET/POST | /mi_memoria | Obtener o actualizar memoria |
| GET | /mis_nichos | Lista de nichos del usuario |
| POST | /tareas | Crear tarea |
| GET | /tareas | Listar tareas |
| POST | /exportar_csv | Registrar exportación de CSV |
| GET | /historial | Historial de exportaciones |
| POST | /estado_lead | Upsert del estado de un dominio |
| GET | /estado_lead | Consultar estado de un dominio |

## 🗄️ Base de datos

- SQLite ya no es soportado. Configura siempre `DATABASE_URL` apuntando a PostgreSQL.
- Para migrar datos antiguos ejecuta:

```bash
python scripts/migrar_sqlite_a_postgres.py --drop
```

- `usuarios` cuenta con el índice único `ix_usuarios_email_lower` sobre `lower(email)` para evitar duplicados por mayúsculas/minúsculas. El índice `ix_usuarios_id` se eliminó por redundante.
- `leads_extraidos` posee la constraint única `uix_leads_usuario_dominio` que impide guardar el mismo dominio varias veces para un usuario.

Verificación rápida en producción:

```sql
SELECT indexname FROM pg_indexes WHERE tablename IN ('usuarios','leads_extraidos');
```

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

Las pruebas utilizan una base de datos PostgreSQL efímera gracias a
[Testcontainers](https://testcontainers.com/), por lo que no necesitas tener
Postgres instalado localmente.

```bash
python -m py_compile $(git ls-files '*.py')
pytest -q
```

Si tu entorno no permite contenedores, exporta `USE_TESTCONTAINERS=0` y define
`TEST_DATABASE_URL` apuntando a una instancia válida de PostgreSQL.

## 🤝 Contribuciones

¿Quieres ayudar a mejorar OpenSells? Si encuentras un error o tienes una idea, abre un issue o envía un pull request. Revisa la sección de pruebas para asegurarte de que tu contribución no rompa nada.

## 🚀 Próximos pasos

- Configurar autenticación en el entorno de pruebas para que `pytest` se ejecute correctamente.
- Añadir envío de emails real en la página *Emails*.
- Mejorar estilo global (tipografía, botones) y paginación/ordenación de tablas de leads.
- Guardar la última página visitada para restaurarla tras login o refresh.

OpenSells sigue evolucionando hacia un servicio estable de generación de leads con modelo freemium.

**👨‍💻 Ayrton**

*(Generado automáticamente el 10/09/2025.)*

