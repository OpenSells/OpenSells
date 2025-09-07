ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email_lower TEXT;
UPDATE usuarios SET email_lower = LOWER(email) WHERE email_lower IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON usuarios(email_lower);
