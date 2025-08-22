-- Sustituye :email_lower por el correo del usuario en minúsculas
SELECT * FROM usuarios WHERE email_lower = :email_lower;

SELECT nicho, nicho_original, COUNT(*) AS leads
FROM leads_extraidos
WHERE user_email_lower = :email_lower
GROUP BY nicho, nicho_original
ORDER BY leads DESC;

SELECT COUNT(*) FROM lead_tarea WHERE user_email_lower = :email_lower AND completado = false;

SELECT status, current_period_end
FROM suscripciones
WHERE user_email_lower = :email_lower
ORDER BY current_period_end DESC
LIMIT 1;
