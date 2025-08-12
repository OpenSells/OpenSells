# Wrapper Leads SaaS

*Actualizado el 12/08/2025*

## 📦 Actualización README Wrapper Leads SaaS (versión 12/08/2025)

Este documento refleja el estado actual del proyecto tras todas las mejoras e integraciones realizadas hasta esta sesión.

### ✅ Cambios clave recientes

- ✅ **Integración con Stripe (portal de pago):**
  - Se añadió un botón en la página **Mi Cuenta** llamado **"Iniciar suscripción"** que abre directamente el portal de pago de Stripe para gestionar la suscripción del usuario.
  - Se creó el endpoint `/crear_portal_pago` en el backend con FastAPI que genera una sesión de Stripe (ya sea Checkout o Billing Portal).
  - En el frontend se redirige automáticamente al portal de pago de Stripe al crear la sesión.
  - Si el usuario intenta gestionar su suscripción sin haber iniciado una, el backend devuelve un mensaje claro indicando que primero debe suscribirse y el botón de gestión se desactiva en el frontend.

- ✅ **Control de acceso según plan de suscripción:**
  - Se añadió lógica unificada para controlar las funcionalidades permitidas según el plan del usuario (`free`, `pro`, etc.).
  - Se centralizó esta comprobación en un nuevo archivo `plan_utils.py`.
  - Esta lógica ahora se aplica a las siguientes páginas:
    - **Búsqueda de leads:** los usuarios con plan `free` no pueden lanzar nuevas búsquedas y se muestra advertencia clara.
    - **Mis Nichos:** usuarios `free` pueden ver sus nichos, pero no pueden eliminar, editar ni lanzar nuevas búsquedas desde nichos. Se muestra advertencia adecuada.
    - **Tareas:** los usuarios `free` no pueden marcar tareas como completadas ni agregar nuevas.
    - **Asistente Virtual:** bloqueado completamente para usuarios sin plan activo, con aviso explicativo.

- ✅ **Botón global de reinicio de caché:**
  - Disponible en todas las páginas desde la barra lateral.
  - Limpia `st.cache_data` y `st.cache_resource`, y ejecuta `st.rerun()` para refrescar toda la interfaz.

- ✅ **Reinicio de caché automático tras ciertas acciones:**
  - Se ejecuta automáticamente tras extraer leads, eliminar nichos o actualizar memoria de usuario.

- ✅ **Corrección del borrado de nichos:**
  - Se armonizó la lógica entre frontend y backend, enviando correctamente `DELETE` y eliminando también los leads relacionados desde PostgreSQL.
  - Se proporciona feedback visual con `st.success()` o `st.error()` según resultado.

### 📊 Estado actual

- **Backend:**
  - FastAPI + SQLAlchemy + PostgreSQL.
  - Endpoints funcionales para gestión de usuarios, nichos, leads, suscripciones y exportaciones.
  - Stripe API operativa desde backend para creación de sesiones de pago.

- **Frontend:**
  - Streamlit multipágina con integración completa al backend.
  - Gestión de leads por nicho, tareas, notas, asistente y exportaciones.
  - Capación por plan de suscripción aplicada en las funciones clave.
  - Portal de pago funcional desde la sección **Mi Cuenta**.

- **Pruebas:**
  - El backend está operativo y se testea manualmente.
  - Pendiente corregir la configuración de `pytest` (falla por errores de base de datos en entorno de test).
- `pip install -r requirements.txt` funcional.

### 🛠️ Ejecución local

1. Clona el repositorio e instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Inicia el backend:

   ```bash
   uvicorn backend.main:app --reload
   ```

3. Inicia el frontend:

   ```bash
   streamlit run streamlit/Home.py
   ```

Esto levantará la API en `http://localhost:8000` y la interfaz de Streamlit en `http://localhost:8501`.

### 🔑 Configuración de variables de entorno

Antes de ejecutar los servicios asegúrate de definir tus variables de entorno. El repositorio incluye un archivo de ejemplo que puedes copiar:

```bash
cp .env.example .env
```

Completa el archivo `.env` con las credenciales necesarias (PostgreSQL, claves de Stripe, etc.) para que el backend y el frontend funcionen correctamente.

### 🚀 Próximos pasos sugeridos

- Configurar entorno de test separado (SQLite en memoria o base de datos temporal) para hacer funcionar `pytest`.
- Implementar validación de plan también desde backend si se quiere evitar bypass.
- Agregar más acciones con lógica condicional según el plan (por ejemplo, límites de tareas o leads por día).
- Añadir log visual de historial de cambios por lead (acciones, tareas, estado).
- Continuar reforzando documentación técnica y modularizando funciones en carpetas `utils`.

---

Wrapper Leads SaaS avanza hacia un sistema estable y escalable, combinando extracción de leads, gestión inteligente, lógica de suscripción y preparación para un modelo freemium real.

**👨‍💻 Ayrton**

*(Generado automáticamente el 12/08/2025 según la conversación y cambios aplicados.)*
