# Wrapper Leads SaaS

## 📦 Actualización README Wrapper Leads SaaS (versión 14/07/2025)

Este documento incluye todos los cambios recientes:

### ✅ Actualizaciones clave desde el 07/07/2025

- ✅ Se solucionó el error de `404 Not Found` en el endpoint `/mover_lead` causado por el doble slash en `BACKEND_URL`. Se añadió `.rstrip("/")` en `cache_utils.py` para evitar errores de ruta.
- ✅ Se reorganizó la carga de variables de entorno para asegurar que `BACKEND_URL` esté definido antes de importar `cache_utils`.
- ✅ Se corrigió la importación de `normalizar_nicho` moviendo `utils.py` a `backend/` y usando `from backend.utils import normalizar_nicho`.
- ✅ Se depuraron errores de caché en Streamlit:
  - Se añadió `limpiar_cache()` tras editar, mover o eliminar leads o tareas.
  - Se reemplazó `st.experimental_rerun()` por `st.rerun()` en todo el frontend.
  - Se implementó `nocache=True` en `cached_get()` para forzar recarga en acciones específicas.
- ✅ Se corrigió el bug en `/buscar_leads` (422) asegurando que el parámetro `query` se envíe correctamente como `query={"query": ...}`.
- ✅ Se añadió `import time` solo una vez al inicio donde se necesitaba para evitar errores de caché.
- ✅ Se solucionó la falta de actualización visual tras guardar o modificar tareas.
- ✅ Se corrigieron errores de `TypeError` en `cached_get()` cuando se pasaban parámetros incorrectos (como `tipo="general"` directamente en vez de en `query={}`).
- ✅ Se implementó correctamente el uso de `limpiar_cache()` en:
  - Creación, edición y borrado de tareas.
  - Guardado de información extra de leads.
  - Movimiento de leads entre nichos.
- ✅ Se reorganizó el módulo `3_Tareas.py` para asegurar la recarga visual inmediata tras cada acción.
