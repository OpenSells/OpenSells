CREATE TABLE IF NOT EXISTS usuario_memoria (
    email_lower TEXT PRIMARY KEY,
    descripcion TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
