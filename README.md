# OpenSells

## Resumen del producto
OpenSells es una plataforma SaaS de prospección B2B que combina un frontend Streamlit multipágina y una API FastAPI para descubrir, deduplicar y gestionar leads con enfoque multi-tenant. La solución cubre todo el ciclo: generación de variantes de búsqueda enriquecidas, scraping asistido con heurísticas y LLMs, gestión de nichos, tareas y métricas, además de un asistente conversacional que opera sobre los mismos endpoints seguros.

## Arquitectura
```
Streamlit (Home.py + pages/*) ── HTTP ──▶ FastAPI (backend/main.py)
        │                                   │
        │                                   ├─ PostgreSQL via SQLAlchemy + Alembic
        │                                   ├─ Stripe webhooks / billing (backend/webhook.py)
        │                                   ├─ Scraping helpers + LLMs (scraper/*)
        │                                   └─ Integraciones externas (ScraperAPI, Google Maps, etc.)
```
- **Frontend**: Streamlit conserva sesión, gestiona autenticación y renderiza dashboards por página (Home, Búsqueda, Nichos, Tareas, Global Search, Mi Cuenta, Asistente, Suscripción).
- **Backend**: FastAPI expone endpoints REST autenticados con JWT, resuelve planes/límites, orquesta scraping y cuenta usos mensuales.
- **Persistencia**: PostgreSQL (multi-tenant por `user_email_lower`) gestionado con SQLAlchemy y Alembic; soporta scripts de migración entre SQLite y Postgres.

## Instalación y requisitos previos
1. **Python 3.11.8** (misma versión usada en Render para garantizar compatibilidad).
2. **PostgreSQL** accesible vía `DATABASE_URL` (se fuerza `sslmode=require` cuando aplica). SQLite solo se usa para migraciones legadas.
3. Clona el repositorio y crea un entorno virtual:
   ```bash
   git clone <URL>
   cd OpenSells
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Dependencias principales (incluidas en `requirements.txt`): FastAPI, Uvicorn, SQLAlchemy, Alembic, Passlib, python-jose, Streamlit, Requests, OpenAI, Stripe, ScraperAPI SDK, BeautifulSoup4, Pandas, Pydantic, Pytest, python-dotenv.

## Ejecución local (backend + frontend)
1. **Configura variables** en `.env` (ver sección siguiente) o exporta en tu shell.
2. **Aplica migraciones**:
   ```bash
   alembic upgrade head
   ```
3. **Levanta la API**:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
4. **Arranca el frontend** apuntando al backend local:
   ```bash
   export BACKEND_URL="http://localhost:8000"
   streamlit run streamlit_app/Home.py
   ```
5. (Opcional) Usa los scripts de datos para poblar información demo (`scripts/`).

## Variables de entorno
| Variable | Descripción | Obligatoria | Notas |
| --- | --- | --- | --- |
| `DATABASE_URL` | Cadena de conexión Postgres usada por SQLAlchemy. | Sí | Añade `?sslmode=require` si Render/Cloud lo exige. |
| `SECRET_KEY` | Clave JWT para firmar tokens. | Sí (prod.) | En dev puede autogenerarse, pero no es recomendado. |
| `BACKEND_URL` | URL base consumida por el frontend. | No | Por defecto `http://localhost:8000`. |
| `OPENAI_API_KEY` | Token para asistente y enriquecimiento de scraping. | No | Si falta, el asistente se deshabilita. |
| `SCRAPERAPI_KEY` | Integra ScraperAPI en la pipeline de scraping. | No | Mejora tasa de éxito en sitios bloqueantes. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Gestión de facturación y webhooks. | No | Necesarios para planes Starter/Pro/Business. |
| `STRIPE_PRICE_FREE/STARTER/PRO/BUSINESS` | IDs de precios Stripe mapeados a planes internos. | No | Caen a plan Free si falta el mapeo. |
| `STRIPE_PORTAL_RETURN_URL` | Redirección tras gestionar la suscripción. | No | Usado por la página de Suscripción. |
| `ASSISTANT_EXTRACTION_ENABLED` | Flag para permitir extracción desde el asistente. | No | Si es `false`, muestra mensaje informativo. |
| `ALLOW_ANON_USER` | Habilita usuario demo sin JWT en entornos controlados. | No | Útil para pruebas automatizadas. |
| `DEBUG_UI` | Muestra panel de depuración en Mi Cuenta. | No | Solo recomendable en desarrollo. |
| `WRAPPER_DEBUG` | Forza payloads raw de `/mi_plan` en la UI. | No | Ayuda a depurar planes y cuotas. |
| `ENV` | Controla comportamientos específicos (dev/production). | No | Activa rutas de debug, logging, etc. |

## Planes y límites
| Plan | Leads/mes | Búsquedas incluidas | Mensajes IA/día | Tareas activas máx. | Exportaciones CSV | Otras características |
| --- | --- | --- | --- | --- | --- | --- |
| **Free** | 40 leads (4 búsquedas × 10 leads) | 4 | 5 | 3 | 1 exportación (10 filas) | Acceso al asistente con límites, prioridad de cola 0. |
| **Starter** | 150 créditos de leads | 20 | 20 | 20 | Ilimitadas | Soporte email estándar, prioridad de cola 1. |
| **Pro** | 600 créditos de leads | 60 | 100 | 100 | Ilimitadas | Automatizaciones avanzadas, prioridad de cola 2. |
| **Business** | 2000 créditos de leads | 200 | 500 | 500 | Ilimitadas | SLA personalizado, múltiples seats, prioridad de cola 3. |

**Medición de contadores**
- `/buscar_leads` descuenta créditos de leads, registra guardados/duplicados y marca búsquedas gratuitas consumidas.
- `/exportar_csv`, `/exportar_todos_mis_leads` y exportaciones por nicho incrementan el contador de CSV por usuario.
- `/tareas` y `/tarea_lead` incrementan contadores de tareas mensuales y validan el máximo de activas.
- `/ia` descuenta mensajes diarios de IA.
- Todos los usos se guardan en `user_usage_monthly` por `user_email_lower` y periodo `YYYYMM`.

## Funcionalidades principales
### Leads y scraping
- Generador de variantes: produce hasta cinco consultas, marcando la quinta como `[Búsqueda extendida]` para ampliar cobertura.
- Scraping híbrido (requests + ScraperAPI) con heurísticas para correos, teléfonos y redes; normaliza dominios y evita duplicados por usuario.
- Deduplicación global por `user_email_lower` con advertencias en la UI cuando un lead ya existe en otro nicho del mismo usuario.

### Nichos y gestión de estados
- Agrupación de leads por nicho con normalización y alias visibles.
- Exportaciones CSV por nicho con filtros por estado/contacto.
- Histórico de notas por lead y sincronización con tareas relacionadas.

### Tareas y workflow
- Tareas multiclase (general, nicho, lead) con prioridades, fechas límite y acciones de seguimiento.
- Contadores mensuales de creación y validación de tareas activas según el plan.
- Alertas en la UI al acercarse a los límites de tareas o leads.

### Búsqueda global & filtros
- Buscador global que combina filtros por dominio, estado y nicho, con exportación CSV global.
- Indicadores de leads duplicados y botones rápidos para saltar al nicho correspondiente.

### Exportaciones
- Descarga CSV por nicho, por usuario completo o filtrado global.
- Inclusión de metadatos (estado, notas, fechas) en las exportaciones.

### Panel “Mi Cuenta”
- Resumen de plan, límites y uso actual, mostrando barras de progreso y alertas.
- Botones de actualización de plan vía Stripe y herramientas de depuración para soporte.

### Asistente virtual
- Chat basado en OpenAI con herramientas seguras para consultar leads, tareas y memoria.
- Posibilidad de crear tareas o anotar leads desde la conversación (respetando cuotas).

### Autenticación y multitenencia
- Registro/login con JWT; contraseña hasheada con Passlib y firma con python-jose.
- `user_email_lower` asegura aislamiento de datos en todas las tablas, habilitando multi-tenant real.
- Sesión persistida en Streamlit (`session_state`, query params y LocalStorage) con logout explícito.

## Endpoints destacados
```http
GET /health
  → 200 OK

POST /register
  {"email": "user@example.com", "password": "secret"}
  → 201 Created

POST /login
  {"email": "user@example.com", "password": "secret"}
  → {"access_token": "...", "token_type": "bearer"}

GET /mi_plan (Bearer token)
  → {"plan": "starter", "limits": {...}, "usage": {...}}

POST /buscar_leads
  Headers: Authorization: Bearer <token>
  {"nicho": "clinicas veterinarias", "ciudad": "Madrid", "pais": "ES"}
  → {"guardados": 12, "duplicados": 3, "variantes": [...], "variantes_display": [...], "has_extended_variant": true}

POST /tareas
  {"texto": "Seguimiento demo", "tipo": "general", "prioridad": "media"}
  → {"id": 123, "estado": "pendiente"}

GET /tareas?estado=pendiente
  → [{"id": 123, "texto": "Seguimiento demo", ...}]

POST /exportar_csv
  {"scope": "nicho", "nicho": "veterinarios"}
  → {"status": "ready", "url": "https://..."}

GET /historial
  → [{"tipo": "export_csv", "created_at": "2025-09-10T11:03:00Z", ...}]
```
Otros endpoints relevantes: `/tarea_lead`, `/tareas_pendientes`, `/mi_memoria`, `/estado_lead`, `/plan/usage`, `/plan/limits`, `/debug/incrementar_uso` (solo dev) y endpoints auxiliares esperados por la UI (exportaciones globales, gestión avanzada de leads).

### Mover lead

Regla clave: cada dominio solo puede existir una vez por usuario (`user_email_lower`). Si el lead ya pertenece a otro nicho del mismo usuario, el backend responde con conflicto.

```bash
curl -X POST "$BACKEND_URL/mover_lead" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dominio": "ejemplo.com",
    "nicho_origen": "Dentistas Murcia",
    "nicho_destino": "Dentistas Valencia",
    "actualizar_nicho_original": false
  }'
```

Respuestas posibles:

- `200 OK`

  ```json
  {"ok": true, "dominio": "ejemplo.com", "de": "Dentistas Murcia", "a": "Dentistas Valencia"}
  ```

- `404 Not Found`

  ```json
  {"detail": "Lead no encontrado en el nicho de origen."}
  ```

- `409 Conflict`

  ```json
  {"detail": "El lead ya existe en el nicho 'dentistas valencia'."}
  ```

### Gestión de leads (info extra, notas, estado, eliminación)

Todos los endpoints requieren el encabezado `Authorization: Bearer <TOKEN>` y respetan la regla de un dominio por usuario.

```bash
curl -X GET "$BACKEND_URL/info_extra" \
  -H "Authorization: Bearer <TOKEN>" \
  -G --data-urlencode "dominio=ejemplo.com"
```

Respuesta `200 OK`:

```json
{
  "dominio": "ejemplo.com",
  "estado_contacto": "pendiente",
  "nicho": "dentistas_murcia",
  "nicho_original": "Dentistas Murcia",
  "email": null,
  "telefono": null,
  "informacion": null,
  "notas": [
    {"id": 42, "texto": "Llamar el lunes", "timestamp": "2025-03-01T10:15:00+00:00"}
  ],
  "tareas_pendientes": 2,
  "tareas_totales": 3
}
```

```bash
curl -X POST "$BACKEND_URL/guardar_info_extra" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dominio": "ejemplo.com",
    "email": "contacto@ejemplo.com",
    "telefono": "+34 600 000 000",
    "informacion": "Cliente interesado en web y RRSS"
  }'
```

Respuesta `201 Created` la primera vez (luego `200 OK` en actualizaciones):

```json
{"ok": true, "dominio": "ejemplo.com", "created": true}
```

```bash
curl -X POST "$BACKEND_URL/nota_lead" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dominio": "ejemplo.com",
    "texto": "Enviar propuesta"
  }'
```

Respuesta `201 Created`:

```json
{"id": 43, "texto": "Enviar propuesta", "timestamp": "2025-03-01T12:00:00+00:00"}
```

```bash
curl -X POST "$BACKEND_URL/leads/estado_contacto" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dominio": "ejemplo.com",
    "estado_contacto": "contactado"
  }'
```

Estados permitidos: `pendiente`, `contactado`, `cerrado`, `fallido`. También se mantiene el shim `PATCH /leads/{lead_id}/estado_contacto` para llamadas legadas.

```bash
curl -X DELETE "$BACKEND_URL/eliminar_lead" \
  -H "Authorization: Bearer <TOKEN>" \
  -G --data-urlencode "nicho=dentistas-murcia" \
  --data-urlencode "dominio=ejemplo.com" \
  --data-urlencode "solo_de_este_nicho=true"
```

Respuesta `200 OK`:

```json
{"ok": true, "dominio": "ejemplo.com"}
```

Si el dominio no existe para el usuario autenticado, los endpoints devuelven `404 Not Found` con `{ "detail": "Lead no encontrado." }`.

#### Mover lead

```bash
curl -X POST "$BACKEND_URL/mover_lead" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dominio": "ejemplo.com",
    "origen": "Dentistas Murcia",
    "destino": "Dentistas Valencia",
    "actualizar_nicho_original": false
  }'
```

Respuestas habituales:

* `200 OK` – `{ "ok": true, "dominio": "ejemplo.com", "de": "Dentistas Murcia", "a": "Dentistas Valencia" }`
* `404 Not Found` – `{ "detail": "Lead no encontrado en el nicho de origen." }`
* `409 Conflict` – `{ "detail": "El lead ya existe en el nicho 'dentistas-valencia'." }`

## Base de datos y migraciones
- Esquema documentado en `AUDITORIA_TABLAS.md`; entidades clave: `usuarios`, `leads_extraidos`, `lead_estado`, `lead_tarea`, `lead_nota`, `user_usage_monthly`, `historial`.
- Claves únicas y `CHECK` basados en `user_email_lower` para garantizar multi-tenant.
- Migraciones gestionadas con Alembic (`alembic upgrade head`).
- Scripts de mantenimiento:
  - `scripts/migrar_sqlite_a_postgres.py`: migra datos principales desde instancias SQLite legadas.
  - `scripts/migrar_memoria_sqlite_a_postgres.py`: migra memorias/conversaciones del asistente.
  - `backend/scripts/migrate_emails_lowercase.py`: normaliza correos existentes a minúsculas.
- Otros utilitarios SQL en `backend/sql/` (por ejemplo, `ensure_lead_tarea_timestamp.sql`).

## Pruebas
- Suite basada en Pytest (`pytest`), con fixtures para Postgres (Testcontainers o `TEST_DATABASE_URL`).
- Tests cubren: límites de planes, deduplicación de leads, API de tareas, exportaciones, multi-tenant y generación de variantes.
- Ejecuta toda la suite:
  ```bash
  pytest
  ```
- Para pruebas rápidas de endpoints se proveen scripts `scripts/local_tests.sh` y colecciones REST.

## Despliegue
- Deploy objetivo en Render (Web Service) con Python 3.11.8 y build command `pip install -r requirements.txt && alembic upgrade head`.
- Variables de entorno y secrets configurados en Render Dashboard.
- El frontend Streamlit puede desplegarse como servicio separado apuntando al backend Render (`BACKEND_URL`).
- Uso de `render.yaml` como referencia de infraestructura.

## Roadmap (Septiembre 2025)
1. **Frontend React**: migrar gradualmente las vistas críticas de Streamlit a una SPA React consumiendo la misma API.
2. **Módulo de emails**: automatizar campañas y seguimiento, integrando plantillas y métricas.
3. **Google Places y enriquecimiento**: añadir orígenes adicionales (Google Places API, redes locales) para ampliar leads.
4. **Analíticas avanzadas**: paneles comparativos de rendimiento, conversión y calidad de leads por nicho.
5. **Automatizaciones**: triggers basados en tareas/comportamiento para generar secuencias.

## Contribución
1. Crea un fork y rama feature (`git checkout -b feature/nombre`).
2. Sigue el estilo existente (PEP8, convenciones de archivos Streamlit) y añade tests cuando corresponda.
3. Ejecuta `pytest` y `alembic upgrade head` antes de abrir un PR.
4. Asegúrate de que el README y los endpoints documentados se mantienen actualizados.
5. Abre el PR detallando cambios, tests y consideraciones de despliegue.

¡Gracias por contribuir a OpenSells!
