-- Idempotent patch to guarantee timestamp defaults on lead_tarea.
-- Ejecutar solo si no se usan migraciones automatizadas.

ALTER TABLE public.lead_tarea
  ALTER COLUMN "timestamp" SET DEFAULT now();

UPDATE public.lead_tarea
SET "timestamp" = now()
WHERE "timestamp" IS NULL;

ALTER TABLE public.lead_tarea
  ALTER COLUMN "timestamp" SET NOT NULL;
