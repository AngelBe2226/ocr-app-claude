#!/usr/bin/env bash
# Arranca "Mis Finanzas" en http://localhost:8000
# Uso:  ./run.sh   (o:  bash run.sh)
cd "$(dirname "$0")" || exit 1

PORT="${1:-8000}"
echo "───────────────────────────────────────────────"
echo "  Mis Finanzas → http://localhost:${PORT}"
echo "  Usuario: angelgbct@gmail.com"
echo "  Contraseña: finanzas123"
echo "  (Ctrl+C para parar)"
echo "───────────────────────────────────────────────"
exec python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port "${PORT}"
