# Auditoría de tablas

## Tablas activas
- usuarios
- user_usage_monthly
- leads_extraidos
- lead_tarea
- lead_historial
- lead_nota
- lead_info_extra
- usuario_memoria
- historial
- lead_estado

## Índices y constraints clave
- `usuarios`: índice único `ix_usuarios_email_lower` sobre `lower(email)`; evita duplicados de emails sin distinguir mayúsculas. Se eliminó el índice redundante `ix_usuarios_id`.
- `leads_extraidos`: constraint único `uix_leads_usuario_dominio` para impedir dominios duplicados por usuario.
- `historial`: índice sobre `user_email` para listar exportaciones por usuario.
- `lead_estado`: índice `ix_lead_estado_user_email_lower` y constraint único `uix_lead_estado_usuario_dominio` para evitar estados duplicados.

## Tablas legadas eliminadas
- users (reemplazada por `usuarios`)
- usage_counters (reemplazada por `user_usage_monthly`)

## Recrear esquema de BD (Alembic)

1. `pip install -r requirements.txt`
2. Definir `DATABASE_URL` (añade `?sslmode=require` si el host lo necesita)
3. `alembic upgrade head`

Para reiniciar una base usa otra instancia o ejecuta:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

Verifica con `alembic current` y lista tablas (`\\dt` en `psql`). No compartas credenciales en el repositorio.
