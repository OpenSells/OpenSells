CREATE INDEX IF NOT EXISTS idx_susc_email_lower ON public.suscripciones(user_email_lower);
CREATE INDEX IF NOT EXISTS idx_susc_status_end  ON public.suscripciones(status, current_period_end DESC);
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON public.usuarios (LOWER(email));
