
# Proyecto Backend — Guía actualizada 15-09-2025 (FastAPI + PostgreSQL)

Este README recoge **todo lo aprendido en el debug reciente** (errores de columnas faltantes, diferencias de esquema y fixes rápidos) y deja un checklist para levantar el backend sin 500s.

---

## Stack

- **FastAPI** + Uvicorn
- **SQLAlchemy** (ORM)
- **PostgreSQL**
- Entorno local Windows (los ejemplos de logs muestran rutas `C:\Users\...`)

---

## Variables de entorno

- `DATABASE_URL` (formato PostgreSQL). Ejemplo:
  ```
  postgresql://<USER>:<PASS>@<HOST>:5432/<DBNAME>?sslmode=require
  ```
  > En los logs aparece `:None` como puerto; si no especificas, Postgres usa el **5432** por defecto, y la conexión funciona igualmente.

---

## Endpoints observados y estado esperado

- `POST /login` → **200 OK**
- `GET /me` → **200 OK**
- `GET /plan/limits` → **200 OK**
- `GET /subscription/summary` → **200 OK**
- `GET /mi_memoria` → **200 OK** (tras fix de `usuario_memoria.descripcion`)
- `GET /mis_nichos` → **200 OK**
- **(Requerían fix de esquema)** `GET /plan/quotas`, `GET /mi_plan`, `GET /plan/usage`,
  `GET /usage`, `GET /stats/usage`, `GET /me/usage`

---

## Esquema de BD (referencia mínima que el código espera)

### Tabla `usuarios`
Campos vistos por la app (log de arranque):
- `id`
- `email`
- `user_email_lower` *(email en minúsculas para búsquedas/joins case-insensitive)*
- `hashed_password`
- `plan`
- `suspendido`
- `fecha_creacion`

### Tabla `lead_tarea` (según la BD real)
> **No tiene `email`**, solo `user_email_lower` (esto causó 500s).
- `id` *(integer)*
- `user_email_lower` *(varchar(255))*
- `dominio` *(varchar(255))*
- `texto` *(text)*
- `fecha` *(timestamp)*
- `completado` *(boolean)*
- `timestamp` *(timestamp)*
- `tipo` *(varchar(50))*
- `nicho` *(varchar(255))*
- `prioridad` *(varchar(10))*
- `auto` *(boolean)*

### Tabla `user_usage_monthly`
> El ORM selecciona también `created_at` y `updated_at`.
- `id`
- `user_id`
- `period_yyyymm` *(p. ej. `202509`)*
- `leads` *(int, default 0)*
- `ia_msgs` *(int, default 0)*
- `tasks` *(int, default 0)*
- `csv_exports` *(int, default 0)*
- `created_at` *(timestamp, default now())*
- `updated_at` *(timestamp, default now())*

### Tabla `usuario_memoria`
> El código lee `email_lower` (PK), `descripcion`, `updated_at`.
- `email_lower` *(PK)*
- `descripcion` *(text, default '')*
- `updated_at` *(timestamp, default now())*

---

## Hotfix SQL **idempotente** (copiar/pegar y ejecutar)

Estos parches corrigen exactamente los errores observados en los logs:

```sql
BEGIN;

-- 1) USAGE MENSUAL: columnas esperadas por el ORM
ALTER TABLE public.user_usage_monthly
  ADD COLUMN IF NOT EXISTS leads        integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS ia_msgs      integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS tasks        integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS csv_exports  integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_at   timestamp without time zone NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS updated_at   timestamp without time zone NOT NULL DEFAULT now();

-- (Opcional pero recomendado) índice y unicidad por usuario/mes
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_usage_monthly_user_period'
  ) THEN
    ALTER TABLE public.user_usage_monthly
      ADD CONSTRAINT uq_user_usage_monthly_user_period UNIQUE (user_id, period_yyyymm);
  END IF;
END $$;

-- 2) LEAD_TAREA: compatibilidad con código que aún selecciona "email"
ALTER TABLE public.lead_tarea
  ADD COLUMN IF NOT EXISTS email varchar(255);

-- Inicializa "email" con el valor de "user_email_lower" cuando esté vacío (una sola vez)
UPDATE public.lead_tarea
   SET email = user_email_lower
 WHERE (email IS NULL OR email = '');

-- Índice útil para queries: por usuario y estado de completado
CREATE INDEX IF NOT EXISTS ix_lead_tarea_user_done
  ON public.lead_tarea (user_email_lower, completado);

-- 3) USUARIO_MEMORIA: columnas usadas por /mi_memoria
--   Crea la tabla si no existe (compatibilidad)
CREATE TABLE IF NOT EXISTS public.usuario_memoria (
  email_lower varchar(255) PRIMARY KEY,
  descripcion text NOT NULL DEFAULT '',
  updated_at  timestamp without time zone NOT NULL DEFAULT now()
);

--   O bien asegura las columnas si la tabla ya existe
ALTER TABLE public.usuario_memoria
  ADD COLUMN IF NOT EXISTS descripcion text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS updated_at  timestamp without time zone NOT NULL DEFAULT now();

COMMIT;
```

> **Por qué este parche:**  
> - Los 500s en `/plan/quotas`, `/plan/usage`, `/usage`, `/stats/usage`, `/me/usage` venían de:
>   - `user_usage_monthly.created_at` inexistente,
>   - `lead_tarea.email` inexistente,
>   - `usuario_memoria.descripcion` inexistente.
> - Todo lo anterior queda cubierto con los `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.

---

## Notas sobre `user_email_lower` (¿qué es y por qué?)

- Es el **email del usuario en minúsculas**, pensado para:
  - **Joins** y filtros insensibles a mayúsculas/minúsculas.
  - Aislamiento por usuario (multi-tenant suave).
- En `lead_tarea` **no hay `email`** real, solo `user_email_lower`.  
  Por compatibilidad con código legado que aún selecciona `lead_tarea.email`, añadimos una columna `email` espejada. A futuro, conviene **retirar** ese campo del modelo y usar siempre `user_email_lower`.

---

## Comprobaciones rápidas post-parche

```sql
-- 1) ¿Sigue faltando alguna columna?
SELECT column_name
FROM information_schema.columns
WHERE table_name IN ('user_usage_monthly', 'lead_tarea', 'usuario_memoria')
ORDER BY table_name, ordinal_position;

-- 2) ¿Devuelven resultados sin 500?
--    (siempre con la app levantada)
-- GET /me
-- GET /plan/limits
-- GET /subscription/summary
-- GET /plan/quotas
-- GET /plan/usage
-- GET /usage
-- GET /stats/usage
-- GET /me/usage
-- GET /mi_memoria
-- GET /mis_nichos

-- 3) ¿Existe fila de usage del mes actual?
SELECT *
FROM public.user_usage_monthly
WHERE user_id = 2 AND period_yyyymm = to_char(now(), 'YYYYMM');
```

---

## Ejecución local

```bash
# Activar virtualenv (Windows PowerShell)
.\env\Scripts\Activate.ps1

# Lanzar la API (reload en dev)
uvicorn backend.main:app --reload
```

Deberías ver en consola líneas como:
```
INFO:     Application startup complete.
INFO:     127.0.0.1:XXXXX - "POST /login HTTP/1.1" 200 OK
...
```

---

## Roadmap técnico (sugerido)

1. **Migraciones Alembic** para formalizar estos cambios (evitar parches manuales).
2. **Eliminar `lead_tarea.email` del ORM** y reemplazarlo por `user_email_lower` en todas las lecturas.
3. **Normalizar timestamps** (idealmente `timestamptz`) y políticas de actualización de `updated_at`.
4. **Tests de integración** para `/plan/*` y `/usage` que fallen si falta alguna columna.

---

## FAQ

- **¿Por qué en los logs la conexión muestra `:None` como puerto?**  
  Porque no se pasó puerto en `DATABASE_URL`. Postgres usa 5432 por defecto y la conexión es válida.

- **¿Qué formato lleva `period_yyyymm`?**  
  Una cadena `YYYYMM` (p. ej. `202509`). El código filtra por ese literal.

---

Si algo vuelve a romper tras aplicar el SQL de arriba, copia el error exacto del log y reabrimos el diagnóstico.
