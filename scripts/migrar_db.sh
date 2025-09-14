#!/usr/bin/env bash
set -e

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL no está definida" >&2
  exit 1
fi

echo "Verificando heads actuales..."
HEADS=$(alembic heads | awk '{print $1}')
COUNT=$(echo "$HEADS" | wc -w)
echo "$HEADS"
if [ "$COUNT" -gt 1 ]; then
  echo "⚠️ Hay múltiples heads: $HEADS"
  echo "Ejecuta: alembic merge -m \"merge parallel heads\" $HEADS"
fi

echo "Aplicando migraciones..."
alembic upgrade head

echo "Heads después de migrar:"
alembic heads

echo "Revisa que las tablas existan en tu BD."
