# OpenSells

## Resumen del producto
OpenSells es una plataforma de prospección que combina un frontend Streamlit multipágina con una API FastAPI para extraer, deduplicar y gestionar leads provenientes de la web y Google Maps.【F:streamlit_app/app.py†L32-L74】 El inicio reúne accesos rápidos al asistente virtual, a la búsqueda clásica de leads, a la gestión de nichos, tareas, exportaciones y a la página de cuenta, mostrando métricas de actividad para cada usuario autenticado.【F:streamlit_app/Home.py†L90-L165】

## Arquitectura
```
Streamlit (Home.py + pages/*) ── HTTP ──▶ FastAPI (backend/main.py)
        │                                   │
        │                                   ├─ PostgreSQL vía SQLAlchemy (backend/database.py)
        │                                   ├─ Stripe webhooks (backend/webhook.py)
        │                                   └─ Herramientas de scraping + OpenAI (scraper/extractor.py)
```
El frontend guarda el token de sesión y realiza llamadas autenticadas a la API configurando `BACKEND_URL`.【F:streamlit_app/cache_utils.py†L22-L54】 El backend expone endpoints REST, resuelve planes/uso y persiste datos multi-tenant en PostgreSQL.【F:backend/main.py†L67-L511】【F:backend/database.py†L13-L57】 Eventos de Stripe pueden actualizar el plan del usuario,【F:backend/webhook.py†L1-L85】 y las rutinas de scraping utilizan heurísticas + OpenAI para enriquecer contactos.【F:scraper/extractor.py†L1-L119】

## Requisitos e instalación
1. **Python 3.11** (se usa también en Render).【F:runtime.txt†L1-L1】  
2. **PostgreSQL** accesible mediante `DATABASE_URL`; SQLite no está soportado y se fuerza `sslmode=require` cuando procede.【F:backend/database.py†L13-L25】  
3. Clonar el repositorio y crear un entorno virtual:
   ```bash
   git clone <URL>
   cd OpenSells
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Las dependencias incluyen FastAPI, SQLAlchemy, Streamlit, OpenAI, Stripe y utilidades de scraping/test.【F:requirements.txt†L1-L28】

## Ejecución local (backend + frontend)
1. **Configurar `.env` en la raíz** con al menos `DATABASE_URL` (Postgres) y `SECRET_KEY`; añade `BACKEND_URL` y `OPENAI_API_KEY` para habilitar el asistente.
2. **Migrar la base**: `alembic upgrade head` (el proyecto ya trae el entorno Alembic preparado y las pruebas lo ejecutan automáticamente).【F:backend/alembic/env.py†L1-L39】【F:tests/conftest.py†L7-L28】
3. **Levantar la API**: 
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   El script de despliegue usa el mismo módulo (`backend.main`) cambiando solo el puerto en producción.【F:backend/start.sh†L1-L2】
4. **Iniciar Streamlit** apuntando al backend local:
   ```bash
   export BACKEND_URL="http://localhost:8000"
   streamlit run streamlit_app/Home.py
   ```
   La aplicación conserva el token en `session_state`, query params y LocalStorage para restaurar la sesión automáticamente.【F:streamlit_app/Home.py†L166-L204】【F:streamlit_app/utils/auth_session.py†L43-L127】

## Variables de entorno
| Variable | Descripción | Obligatoria | Notas |
| --- | --- | --- | --- |
| `DATABASE_URL` | Cadena Postgres usada por SQLAlchemy; se carga desde `.env` y se valida que no sea SQLite. | Sí | Añade `?sslmode=require` si el proveedor lo necesita.【F:backend/database.py†L13-L25】 |
| `SECRET_KEY` | Clave JWT de la API; en producción debe proporcionarse explícitamente. | Sí (prod.) | En entornos no productivos se genera una clave temporal si falta.【F:backend/auth.py†L17-L23】 |
| `BACKEND_URL` | URL base que consume el frontend y los helpers de cuenta. | No | Por defecto `http://localhost:8000`.【F:streamlit_app/cache_utils.py†L22-L33】【F:streamlit_app/ui/account_helpers.py†L5-L35】 |
| `OPENAI_API_KEY` | Token para el asistente y para el extractor web. | No | Si falta, la página del asistente se deshabilita.【F:streamlit_app/cache_utils.py†L28-L33】【F:scraper/extractor.py†L13-L15】 |
| `SCRAPERAPI_KEY` | Clave opcional para integrar ScraperAPI en flujos de scraping. | No | La dependencia `scraperapi-sdk` está incluida para entornos que lo usen.【F:requirements.txt†L10-L14】 |
| `STRIPE_PRICE_FREE/STARTER/PRO/BUSINESS` | IDs de precios Stripe mapeados a planes internos en la API. | No | Si el price_id no se reconoce, el usuario cae a plan `free`.【F:backend/core/stripe_mapping.py†L6-L19】 |
| `STRIPE_PRICE_GRATIS/BASICO/PREMIUM` | IDs que la UI usa para lanzar el portal de pagos. | No | Se leen desde `.env` o `st.secrets`.【F:streamlit_app/pages/7_Suscripcion.py†L53-L135】 |
| `ASSISTANT_EXTRACTION_ENABLED` | Flag que bloquea la extracción de leads desde el asistente cuando vale `false`. | No | El backend devuelve un placeholder si está desactivado.【F:streamlit_app/assistant_api.py†L11-L27】【F:backend/deps.py†L1-L12】 |
| `ALLOW_ANON_USER` | Permite que la API devuelva un usuario ficticio sin token (útil en tests). | No | Solo habilitar en entornos controlados.【F:backend/auth.py†L47-L67】 |
| `ENV` | Controla comportamientos de depuración (por ejemplo, routers de debug y generación de SECRET_KEY). | No | Valores comunes: `dev`, `production`.【F:backend/main.py†L50-L59】【F:backend/auth.py†L17-L23】 |
| `DEBUG_UI` | Activa el panel de depuración de la página Mi Cuenta. | No | Puede definirse vía `.env` o `st.secrets`.【F:streamlit_app/pages/8_Mi_Cuenta.py†L317-L325】 |
| `WRAPPER_DEBUG` | Fuerza a la UI a mostrar payloads crudos de `/mi_plan`. | No | Se evalúa en los helpers de cuenta.【F:streamlit_app/ui/account_helpers.py†L5-L126】 |
| `BRAND_NAME`, `LEADS_PAGE_PATH`, etc. | Personalizan etiquetas y navegación de Streamlit. | No | Valores por defecto definidos en `utils/constants.py`.【F:streamlit_app/utils/constants.py†L9-L33】 |
| `USE_TESTCONTAINERS` / `TEST_DATABASE_URL` | Controlan la base usada por las pruebas. | No | Por defecto usa Postgres en Testcontainers y recurre a `TEST_DATABASE_URL` si está definido.【F:tests/conftest.py†L5-L28】 |

## Planes y límites
| Plan | Leads/mes | Mensajes IA | Tareas activas máx. | Exportaciones CSV | ¿Notas? | Otros |
| --- | --- | --- | --- | --- | --- | --- |
| Free | ≈40 (4 búsquedas × 10 leads) | 5 | 3 | 1 exportación / 10 filas | Sí (sin tope) | Prioridad de cola 0.【F:backend/core/plan_config.py†L22-L32】【F:backend/models.py†L104-L118】 |
| Básico (`starter`) | 150 créditos | 20 | 20 | Ilimitadas | Sí | Prioridad de cola 1.【F:backend/core/plan_config.py†L33-L40】 |
| Premium (`pro`) | 600 créditos | 100 | 100 | Ilimitadas | Sí | Prioridad de cola 2.【F:backend/core/plan_config.py†L41-L48】 |

> *Business* (`business`) extiende estos límites a 2000 leads y 500 tareas; úsalo para clientes enterprise.【F:backend/core/plan_config.py†L49-L55】

**Cómo se miden los contadores**
- `/buscar_leads` calcula leads guardados/duplicados, descuenta búsquedas gratuitas o créditos y registra el uso mensual de `leads`.【F:backend/main.py†L409-L459】【F:backend/core/usage_helpers.py†L24-L63】
- `/exportar_csv` registra exportaciones y guarda el historial por usuario.【F:backend/main.py†L346-L365】【F:tests/test_historial_estado.py†L11-L16】
- `/ia` incrementa `ia_msgs` cuando se procesa un prompt no vacío.【F:backend/main.py†L378-L406】【F:backend/core/usage_helpers.py†L32-L47】
- Crear una tarea (`/tareas` o `/tarea_lead`) suma al contador mensual `tasks` y aumenta el total de tareas activas hasta el máximo del plan.【F:backend/main.py†L222-L333】【F:backend/core/usage_service.py†L37-L78】【F:backend/core/plan_service.py†L64-L106】

**Corte y edge cases**
- Los consumos se guardan por `period_yyyymm` en la tabla `user_usage_monthly`, de modo que el reset es mensual (formato `YYYYMM`).【F:backend/core/usage_service.py†L20-L78】【F:backend/models.py†L85-L101】
- Cambiar de plan no reinicia los contadores: `PlanService` siempre devuelve el uso acumulado del mes corriente.【F:backend/core/plan_service.py†L58-L117】
- Si Stripe envía un `price_id` desconocido, tanto el webhook como la resolución local del plan hacen fallback a `free`.【F:backend/webhook.py†L69-L83】【F:backend/core/plan_service.py†L28-L50】
- Límites `None` se muestran como “Sin límite” en la UI para evitar divisiones por cero.【F:streamlit_app/pages/8_Mi_Cuenta.py†L258-L292】

**Ejemplo `GET /mi_plan`**
```json
{
  "plan": "starter",
  "limits": {
    "searches_per_month": null,
    "leads_cap_per_search": null,
    "csv_exports_per_month": null,
    "csv_rows_cap_free": null,
    "lead_credits_month": 150,
    "tasks_active_max": 20,
    "ai_daily_limit": 20
  },
  "usage": {
    "leads": {"used": 30, "remaining": 120, "period": "202404"},
    "ia_msgs": {"used": 5, "period": "202404"},
    "tasks": {"used": 2, "period": "202404"},
    "csv_exports": {"used": 1, "remaining": null, "period": "202404"},
    "tasks_active": {"current": 2, "limit": 20}
  },
  "remaining": {
    "leads": 120,
    "csv_exports": null,
    "tasks_active": 18,
    "ia_msgs": null,
    "tasks": null
  }
}
```
Los campos coinciden con la estructura que genera `PlanService.get_quotas`.【F:backend/core/plan_service.py†L58-L117】

## Funcionalidades clave
### Leads y scraping
- La página “Búsqueda” orquesta la búsqueda de dominios, la extracción y la exportación, mostrando estados de proceso y manejando límites de plan.【F:streamlit_app/pages/1_Busqueda.py†L20-L188】
- Cada dominio se normaliza antes de guardarlo y existe un constraint único `user_email_lower + dominio` que evita duplicados por usuario.【F:backend/main.py†L61-L64】【F:backend/models.py†L154-L158】
- Scripts auxiliares (carpeta `scraper/`) extraen emails, teléfonos y redes sociales aplicando heurísticas y resúmenes con OpenAI.【F:scraper/extractor.py†L17-L115】

### Nichos y estados
- Los leads se agrupan por nicho: se almacena el nombre normalizado (`nicho`) y el original para mostrarlo en la UI.【F:backend/models.py†L145-L147】 El helper `normalizar_nicho` mantiene la consistencia al crear nuevos grupos.【F:backend/utils.py†L1-L8】
- La vista de nichos permite filtrar por estado/contacto, exportar CSV por nicho y añadir leads manuales advirtiendo cuando el dominio ya existe en otro nicho del mismo usuario.【F:streamlit_app/pages/3_Mis_Nichos.py†L260-L387】
- El estado de contacto de un lead se gestiona mediante `/estado_lead`, que upserta el registro con `user_email_lower` y dominio normalizado.【F:backend/main.py†L483-L511】

### Tareas e historial
- Las tareas admiten tipos (`general`, `nicho`, `lead`), prioridades y fechas; la UI ofrece filtros y acciones de completar/editar por cada fila.【F:streamlit_app/pages/4_Tareas.py†L1-L240】
- Al crear una tarea se verifica el cupo activo y se incrementa el contador mensual. El backend expone listados (`/tareas`, `/tareas_pendientes`) y crea tareas específicas para leads con `/tarea_lead`.【F:backend/main.py†L222-L333】
- El historial de exportaciones se consulta en `/historial` y se alimenta desde `/exportar_csv`.【F:backend/main.py†L346-L475】【F:tests/test_historial_estado.py†L11-L16】

### Búsqueda global y exportaciones
- La página de nichos ofrece un buscador global por dominio, filtros combinables por estado y descarga de CSV filtrados por nicho.【F:streamlit_app/pages/3_Mis_Nichos.py†L298-L384】
- Mi Cuenta intenta exponer un CSV global (`/exportar_todos_mis_leads`) y endpoints de debug (`/debug-db`, `/debug-user-snapshot`); estos endpoints deben existir en despliegues completos aunque no estén presentes en este backend minimalista.【F:streamlit_app/pages/8_Mi_Cuenta.py†L379-L470】

### Panel “Mi Cuenta”
- Normaliza las métricas de `/mi_plan`/`/plan/quotas`, traduce alias frecuentes y pinta barras de progreso para búsquedas, mensajes IA, leads mensuales y tareas activas.【F:streamlit_app/pages/8_Mi_Cuenta.py†L21-L292】
- El pie muestra el período mensual en formato humano (mes en español + año).【F:streamlit_app/pages/8_Mi_Cuenta.py†L75-L102】

### Asistente virtual
- Usa OpenAI (`chat.completions`) para generar respuestas, restringe prompts que violan la política (detalles internos, scraping, datos de terceros) y ofrece herramientas para consultar/mutar datos del backend (estado de leads, tareas, memoria).【F:streamlit_app/pages/2_Asistente_Virtual.py†L1-L280】【F:streamlit_app/utils/assistant_guard.py†L1-L35】
- La extracción desde el asistente se puede desactivar globalmente con `ASSISTANT_EXTRACTION_ENABLED`, devolviendo un mensaje placeholder.【F:streamlit_app/assistant_api.py†L11-L27】

### Autenticación y multitenencia
- El backend registra usuarios con email normalizado (`user_email_lower`) y valida credenciales con JWT.【F:backend/auth.py†L30-L82】【F:backend/models.py†L27-L44】
- La UI guarda el token en memoria, query params y LocalStorage, restaurando sesiones salvo que el usuario haya hecho logout (marca `wrapper_logged_out`).【F:streamlit_app/utils/auth_session.py†L43-L127】【F:streamlit_app/utils/auth_utils.py†L28-L68】
- Todas las tablas relevantes (`leads_extraidos`, `lead_tarea`, `lead_estado`, etc.) indexan por `user_email_lower` para aislar datos por usuario.【F:backend/models.py†L45-L205】 Las pruebas verifican el aislamiento creando tareas con usuarios diferentes.【F:tests/test_multi_tenant.py†L9-L22】

## Endpoints
| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/health` | Ping de salud simple. |【F:backend/main.py†L67-L69】
| POST | `/register` | Alta de usuario con email normalizado. |【F:backend/main.py†L83-L110】
| POST | `/login` | Devuelve un JWT válido en `access_token`. |【F:backend/main.py†L113-L124】
| GET | `/me` | Datos básicos del usuario autenticado. |【F:backend/main.py†L127-L129】
| GET | `/mi_plan` | Límites y uso combinados (incluye tareas activas). |【F:backend/main.py†L132-L135】
| GET | `/plan/usage` (`/usage`, `/stats/usage`, `/me/usage`) | Devuelve solo el bloque de uso. |【F:backend/main.py†L138-L146】
| GET | `/plan/limits` (`/limits`) | Límites del plan efectivo. |【F:backend/main.py†L148-L154】
| GET | `/plan/quotas` | Alias directo de `/mi_plan`. |【F:backend/main.py†L157-L160】
| GET | `/plan/subscription`, `/subscription/summary`, `/billing/summary`, `/stripe/subscription` | Placeholder con el plan actual y estado de Stripe. |【F:backend/main.py†L163-L170】
| GET/POST | `/mi_memoria` | Guarda o recupera la memoria del usuario. |【F:backend/main.py†L177-L195】
| GET | `/mis_nichos` | Lista nichos (normalizado + original). |【F:backend/main.py†L199-L208】
| POST | `/tareas` | Crea una tarea general/nicho/lead validando límites. |【F:backend/main.py†L222-L279】
| GET | `/tareas` | Lista de tareas con filtros opcionales. |【F:backend/main.py†L286-L311】
| POST | `/tarea_lead` | Crea una tarea marcada como `lead`. |【F:backend/main.py†L322-L332】
| GET | `/tareas_pendientes` | Lista tareas pendientes (opcional por tipo). |【F:backend/main.py†L333-L341】
| POST | `/exportar_csv` | Registra una exportación y consume cuota. |【F:backend/main.py†L346-L365】
| POST | `/ia` | Consume un mensaje IA si hay prompts válidos. |【F:backend/main.py†L378-L406】
| POST | `/buscar_leads` | Aplica lógica de consumo y devuelve resumen de guardados/duplicados. |【F:backend/main.py†L409-L459】
| GET | `/historial` | Devuelve el historial de exportaciones. |【F:backend/main.py†L462-L475】
| POST/GET | `/estado_lead` | Upsert y consulta de estado por dominio normalizado. |【F:backend/main.py†L483-L511】
| PATCH | `/leads/{id}/estado_contacto` | Actualiza el estado de contacto de un lead guardado. |【F:backend/routers/leads.py†L1-L26】
| POST | `/debug/incrementar_uso` | Disponible en `ENV=dev`; incrementa contadores para pruebas. |【F:backend/main.py†L50-L59】【F:backend/routers/debug.py†L1-L16】

**Endpoints esperados por la UI pero no incluidos en este backend base**
- Exportaciones y mantenimiento de nichos (`/exportar_leads_nicho`, `/eliminar_nicho`, `/exportar_todos_mis_leads`).【F:streamlit_app/pages/3_Mis_Nichos.py†L260-L388】【F:streamlit_app/pages/8_Mi_Cuenta.py†L379-L470】
- Gestión avanzada de tareas (`/tarea_completada`, `/editar_tarea`).【F:streamlit_app/pages/4_Tareas.py†L195-L235】
- Endpoints adicionales del asistente (`/nota_lead`, `/tareas_lead`, `/historial_lead`, `/mover_lead`).【F:streamlit_app/pages/2_Asistente_Virtual.py†L112-L279】
Asegúrate de implementarlos o mockearlos si la UI va a usarse contra este backend.

## BD & Migraciones
- Tablas clave: `usuarios`, `leads_extraidos`, `lead_tarea`, `lead_estado`, `user_usage_monthly`, `lead_nota`, `historial`, todas con índices/constraints en `user_email_lower` para separar tenants.【F:backend/models.py†L24-L205】 El documento `AUDITORIA_TABLAS.md` resume tablas y constraints activos.【F:AUDITORIA_TABLAS.md†L1-L33】
- `UserUsageMonthly` almacena contadores mensuales (`leads`, `ia_msgs`, `tasks`, `csv_exports`) con `period_yyyymm` único por usuario.【F:backend/models.py†L85-L101】
- Ejecuta migraciones con Alembic (`alembic upgrade head`).【F:backend/alembic/env.py†L1-L39】 Para sanear columnas en bases antiguas hay utilidades idempotentes (`backend/startup_migrations.py`, `backend/scripts/migrate_emails_lowercase.py`).【F:backend/startup_migrations.py†L1-L37】【F:backend/scripts/migrate_emails_lowercase.py†L1-L46】

## Pruebas
- Las pruebas automáticas usan Pytest con Testcontainers Postgres por defecto; define `USE_TESTCONTAINERS=0` y `TEST_DATABASE_URL` para reutilizar una base propia.【F:tests/conftest.py†L5-L28】
- Cobertura destacada:
  - Cuotas y aliases de plan (`test_plan_endpoints.py`).【F:tests/test_plan_endpoints.py†L6-L54】
  - Incremento mensual de tareas (`test_usage_monthly_tasks_counter.py`).【F:tests/test_usage_monthly_tasks_counter.py†L8-L35】
  - Aislamiento multi-tenant (`test_multi_tenant.py`).【F:tests/test_multi_tenant.py†L9-L22】
  - Historial y estado de leads (`test_historial_estado.py`).【F:tests/test_historial_estado.py†L8-L27】
- Ejecuta las pruebas con:
  ```bash
  USE_TESTCONTAINERS=0 TEST_DATABASE_URL=postgresql://… pytest
  ```

## Despliegue
Render usa un servicio Python con `uvicorn backend.main:app --host 0.0.0.0 --port 10000` y Python 3.11.8.【F:render.yaml†L1-L11】 El script `backend/start.sh` replica este comando para contenedores. Ajusta `DATABASE_URL`, `SECRET_KEY` y los price IDs de Stripe en la configuración de Render antes de desplegar.【F:backend/start.sh†L1-L2】【F:backend/auth.py†L17-L23】

## Roadmap
- Migrar la UI de Streamlit a una SPA (React) para mejorar UX y performance en producción.【F:streamlit_app/app.py†L32-L74】
- Completar la integración de Stripe (portales de pago, sincronización de planes y webhooks robustos).【F:streamlit_app/pages/7_Suscripcion.py†L90-L135】【F:backend/webhook.py†L54-L85】
- Ampliar el dashboard con analíticas adicionales (conversiones, embudos) sobre la base del panel de uso actual.【F:streamlit_app/pages/8_Mi_Cuenta.py†L258-L292】
- Mejorar heurísticas de scraping/deduplicado y cubrir más fuentes de datos.【F:scraper/extractor.py†L17-L115】【F:backend/main.py†L409-L459】
- Lanzar el módulo de emails (actualmente placeholder) con secuencias y métricas de envíos.【F:streamlit_app/pages/6_Emails.py†L1-L32】
- Definir políticas de uso de Google Places y límites de extracción para planes de pago.【F:streamlit_app/app.py†L40-L69】

## Contribución
1. Crea una rama y trabaja con pull requests descriptivos.  
2. Sigue el patrón de multitenencia (`user_email_lower`) al tocar modelos o endpoints.【F:backend/models.py†L27-L205】【F:backend/main.py†L222-L333】  
3. Actualiza la documentación (este README/Mi Cuenta) cuando cambien límites o métricas.  
4. Ejecuta `pytest` antes de abrir PRs y añade pruebas para nuevas reglas de negocio.【F:tests/conftest.py†L5-L46】  
5. Mantén coherencia con los helpers existentes (p. ej., `_period_humano`, alias de métricas) al ampliar la UI de Streamlit.【F:streamlit_app/pages/8_Mi_Cuenta.py†L21-L292】
