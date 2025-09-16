#!/bin/bash
# Quick smoke tests for /tarea_lead endpoint.
# Configure TOKEN and URL before running (defaults below are placeholders).
TOKEN=${TOKEN:-BEARER_JWT_AQUI}
URL=${URL:-http://127.0.0.1:8000}

set -euo pipefail

function post_tarea() {
    local body=$1
    curl -i -X POST "${URL}/tarea_lead" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${body}"
    echo -e "\n"
}

echo "== GENERAL =="
post_tarea '{"texto":"Probar tarea general","tipo":"general","prioridad":"media"}'

echo "== LEAD =="
post_tarea '{"texto":"Llamar al lead","tipo":"lead","dominio":"ejemplo.com","prioridad":"alta"}'

echo "== NICHO =="
post_tarea '{"texto":"Revisar nicho","tipo":"nicho","nicho":"Dentistas Madrid","prioridad":"baja"}'
