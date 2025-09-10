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

## Índices y constraints clave
- `usuarios`: índice único `ix_usuarios_email_lower` sobre `lower(email)`; evita duplicados de emails sin distinguir mayúsculas. Se eliminó el índice redundante `ix_usuarios_id`.
- `leads_extraidos`: constraint único `uix_leads_usuario_dominio` para impedir dominios duplicados por usuario.

## Tablas legadas eliminadas
- users (reemplazada por `usuarios`)
- usage_counters (reemplazada por `user_usage_monthly`)
