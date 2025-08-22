# OpenSells

*Actualizado el 21/08/2025*

**OpenSells** es un SaaS para generación y gestión de leads apoyado en un backend FastAPI y una interfaz multipágina en Streamlit.

## 🆕 Novedades recientes

- **Autenticación integrada en Home:** formulario combinado de inicio de sesión y registro con botones de ancho completo.
- **Persistencia de sesión y cierre por inactividad:** los JWT se guardan en `localStorage` y se restauran al refrescar; las sesiones expiran tras 20 minutos sin actividad.
- **Control de acceso uniforme:** todas las páginas excepto Home verifican sesión y muestran enlace a Home si el usuario no ha iniciado sesión.
- **Página “Búsqueda” mejorada:** expander con sugerencias de nichos y consejos para mejores leads, selector de nicho seguro y badge de plan en la barra lateral.
- **Página “Emails” (placeholder):** muestra "Disponible próximamente" con vista previa de envío 1:1, masivo y plantillas.
- **Aviso de leads duplicados más discreto:** se reemplazó el warning por una nota sutil.
- **Gestión de sesión y rutas unificada:** refactor para centralizar manejo de tokens y paths en toda la app.
- **Clave multi-tenant unificada:** todos los datos se filtran por `user_email_lower` y se añadió `/debug-user-snapshot` para diagnosticar sesión y base de datos.
- **Validación de `DATABASE_URL`:** el backend avisa al arrancar si apunta a SQLite o falta la variable.
- **Resolución de plan unificada:** función `resolve_user_plan` y endpoint `/mi_plan` para mostrar badge correcto según suscripción.
- **Cliente HTTP centralizado:** todas las llamadas del frontend usan `utils/http_client.py` con cabecera `Authorization` y manejo de `401`.

## 📊 Estado del proyecto

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL; endpoints para usuarios, nichos, leads, tareas, exportaciones y suscripciones (Stripe).
- **Frontend:** Streamlit multipágina con generación de leads, gestión de nichos, tareas, asistente virtual, exportaciones y control de acceso por plan.
- **Autenticación:** JWT persistido en cookies, helper `utils/auth_utils.py` para restaurar sesión y auto-logout.
- **Multi-tenant:** la clave es `user_email_lower`; hay endpoint `/debug-user-snapshot` para verificar sesión y prefijo de la base de datos.
- **Pruebas:** `pytest` devuelve 4 fallos (401) y 1 test pasa; el código compila con `python -m py_compile`.

## 🛠️ Ejecución local

1. Instala dependencias:

```bash
pip install -r requirements.txt
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

*(Generado automáticamente el 21/08/2025.)*
