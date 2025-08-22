ALTER TABLE public.nichos          ADD COLUMN IF NOT EXISTS user_email_lower varchar;
ALTER TABLE public.leads_extraidos ADD COLUMN IF NOT EXISTS user_email_lower varchar;

UPDATE public.nichos
SET user_email_lower = LOWER(email_lower)
WHERE (user_email_lower IS NULL OR user_email_lower = '')
  AND email_lower IS NOT NULL;

UPDATE public.leads_extraidos
SET user_email_lower = LOWER(email_lower)
WHERE (user_email_lower IS NULL OR user_email_lower = '')
  AND email_lower IS NOT NULL;

UPDATE public.nichos          SET user_email_lower = LOWER(user_email_lower);
UPDATE public.leads_extraidos SET user_email_lower = LOWER(user_email_lower);

CREATE INDEX IF NOT EXISTS idx_nichos_user_email_lower ON public.nichos(user_email_lower);
CREATE INDEX IF NOT EXISTS idx_leads_user_email_lower  ON public.leads_extraidos(user_email_lower);
