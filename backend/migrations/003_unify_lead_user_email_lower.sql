ALTER TABLE public.lead_nota ADD COLUMN IF NOT EXISTS user_email_lower varchar;
UPDATE public.lead_nota
SET user_email_lower = LOWER(email_lower)
WHERE (user_email_lower IS NULL OR user_email_lower = '')
  AND email_lower IS NOT NULL;

UPDATE public.leads_extraidos SET user_email_lower = LOWER(user_email_lower);
UPDATE public.nichos SET user_email_lower = LOWER(user_email_lower);
UPDATE public.lead_nota SET user_email_lower = LOWER(user_email_lower);

CREATE INDEX IF NOT EXISTS idx_leads_email_lower ON public.leads_extraidos(user_email_lower);
CREATE INDEX IF NOT EXISTS idx_nichos_email_lower ON public.nichos(user_email_lower);
CREATE INDEX IF NOT EXISTS idx_nota_email_lower ON public.lead_nota(user_email_lower);
