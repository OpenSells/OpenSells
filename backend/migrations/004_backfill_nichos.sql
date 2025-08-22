DO $$
BEGIN
  -- Try to enable unaccent extension; ignore if missing
  BEGIN
    CREATE EXTENSION IF NOT EXISTS unaccent;
  EXCEPTION WHEN undefined_file THEN
    -- extension not available, continue without unaccent
    NULL;
  END;
END$$;

-- Create normalize_nicho helper depending on unaccent availability
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='unaccent') THEN
    EXECUTE $$CREATE OR REPLACE FUNCTION normalize_nicho(txt text)
      RETURNS text
      LANGUAGE sql IMMUTABLE AS $$
        SELECT regexp_replace(lower(unaccent(coalesce($1,''))), '[^a-z0-9]+', '_', 'g')
      $$;$$;
  ELSE
    EXECUTE $$CREATE OR REPLACE FUNCTION normalize_nicho(txt text)
      RETURNS text
      LANGUAGE sql IMMUTABLE AS $$
        SELECT regexp_replace(lower(coalesce($1,'')), '[^a-z0-9]+', '_', 'g')
      $$;$$;
  END IF;
END$$;

-- Unique index to avoid duplicates per user + nicho
CREATE UNIQUE INDEX IF NOT EXISTS ux_nichos_user_nicho
  ON public.nichos(user_email_lower, nicho);

-- Backfill from leads
WITH cte AS (
  SELECT
    lower(user_email_lower) AS user_email_lower,
    normalize_nicho(coalesce(nullif(nicho,''), nicho_original)) AS nicho_norm,
    coalesce(nullif(nicho_original,''), nicho) AS nicho_display
  FROM public.leads_extraidos
  WHERE coalesce(nicho, nicho_original) IS NOT NULL
  GROUP BY 1,2,3
)
INSERT INTO public.nichos (user_email_lower, nicho, nicho_original)
SELECT user_email_lower, nicho_norm, nicho_display
FROM cte
ON CONFLICT (user_email_lower, nicho) DO NOTHING;

-- Normalize owners to lowercase
UPDATE public.nichos SET user_email_lower = LOWER(user_email_lower);

-- Support indexes
CREATE INDEX IF NOT EXISTS idx_nichos_user_email_lower  ON public.nichos(user_email_lower);
CREATE INDEX IF NOT EXISTS idx_leads_user_email_lower   ON public.leads_extraidos(user_email_lower);

-- View for fallback when nichos table empty
CREATE OR REPLACE VIEW v_nichos_usuario AS
SELECT
  lower(user_email_lower) AS user_email_lower,
  normalize_nicho(coalesce(nullif(nicho,''), nicho_original)) AS nicho,
  min(coalesce(nullif(nicho_original,''), nicho)) AS nicho_original,
  COUNT(*) AS total_leads
FROM public.leads_extraidos
WHERE coalesce(nicho, nicho_original) IS NOT NULL
GROUP BY 1,2;

-- Trigger to auto-upsert nicho on new leads
CREATE OR REPLACE FUNCTION upsert_nicho_from_lead()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF coalesce(NEW.nicho, NEW.nicho_original) IS NOT NULL THEN
    INSERT INTO public.nichos (user_email_lower, nicho, nicho_original)
    VALUES (
      lower(NEW.user_email_lower),
      normalize_nicho(coalesce(nullif(NEW.nicho,''), NEW.nicho_original)),
      coalesce(nullif(NEW.nicho_original,''), NEW.nicho)
    )
    ON CONFLICT (user_email_lower, nicho) DO NOTHING;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_upsert_nicho_from_lead ON public.leads_extraidos;
CREATE TRIGGER trg_upsert_nicho_from_lead
AFTER INSERT ON public.leads_extraidos
FOR EACH ROW EXECUTE FUNCTION upsert_nicho_from_lead();
