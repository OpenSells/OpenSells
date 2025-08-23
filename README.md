# OpenSells

*Actualizado el 23/08/2025*

**OpenSells** es un SaaS para generación y gestión de leads apoyado en un backend FastAPI y una interfaz multipágina en Streamlit.

## 🆕 Novedades recientes

- **Memoria del asistente en PostgreSQL:** las interacciones se persisten en una tabla multi-tenant; se incluye script `scripts/migrar_memoria_sqlite_a_postgres.py` para migrar datos previos.
- **Extracción de leads desde el asistente deshabilitada:** se añadió un guard que bloquea estas llamadas para evitar uso no deseado.
- **Autenticación integrada en Home:** formulario combinado de inicio de sesión y registro con botones de ancho completo.
- **Persistencia de sesión y cierre por inactividad:** los JWT se guardan en `localStorage` y se restauran al refrescar; las sesiones expiran tras 20 minutos sin actividad.
- **Control de acceso uniforme:** todas las páginas excepto Home verifican sesión y muestran enlace a Home si el usuario no ha iniciado sesión.
- **Página “Búsqueda” mejorada:** expander con sugerencias de nichos y consejos para mejores leads, selector de nicho seguro y badge de plan en la barra lateral.
- **Página “Emails” (placeholder):** muestra "Disponible próximamente" con vista previa de envío 1:1, masivo y plantillas.
- **Aviso de leads duplicados más discreto:** se reemplazó el warning por una nota sutil.
- **Gestión de sesión y rutas unificada:** refactor para centralizar manejo de tokens y paths en toda la app.
- **Clave multi-tenant unificada:** todos los datos se filtran por `user_email_lower` y se añadió `/debug-user-snapshot` para diagnosticar sesión y base de datos.
- **Esquema multi-tenant armonizado:** las tablas `lead_nota`, `lead_tarea` y asociadas incluyen ahora `user_email_lower` no nulo, se añadieron índices compuestos y el conteo de leads se realiza por dominio distinto vía `/conteo_leads`.
- **Validación de `DATABASE_URL`:** el backend avisa al arrancar si apunta a SQLite o falta la variable.

## 📊 Estado del proyecto

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL; endpoints para usuarios, nichos, leads, tareas, exportaciones y suscripciones (Stripe).
- **Frontend:** Streamlit multipágina con generación de leads, gestión de nichos, tareas, asistente virtual, exportaciones y control de acceso por plan.
- **Autenticación:** JWT persistido en cookies, helper `utils/auth_utils.py` para restaurar sesión y auto-logout.
- **Multi-tenant:** la clave es `user_email_lower`; hay endpoint `/debug-user-snapshot` para verificar sesión y prefijo de la base de datos.
- **Memoria del asistente:** conversaciones almacenadas en PostgreSQL, con soporte de migración desde SQLite.
- **Pruebas:** `pytest` pasa todas las pruebas y el código compila con `python -m py_compile`.

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

## 🔑 Variables de entorno

Copia `.env.example` a `.env` y completa las claves necesarias (PostgreSQL, Stripe, etc.):

```bash
cp .env.example .env
```

## 🚀 Próximos pasos

- Configurar autenticación en el entorno de pruebas para que `pytest` se ejecute correctamente.
- Añadir envío de emails real en la página *Emails*.
- Mejorar estilo global (tipografía, botones) y paginación/ordenación de tablas de leads.
- Guardar la última página visitada para restaurarla tras login o refresh.

OpenSells sigue evolucionando hacia un servicio estable de generación de leads con modelo freemium.

**👨‍💻 Ayrton**

*(Generado automáticamente el 23/08/2025.)*
