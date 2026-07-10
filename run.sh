#!/usr/bin/env bash
# Arranca "MyMoney" en http://localhost:8000 (y en la red local)
# Uso:  ./run.sh            (o:  bash run.sh)
#       ./run.sh 8001       (otro puerto)
#       DATABASE_URL='postgresql://...' ./run.sh   (usar Neon/Postgres)
cd "$(dirname "$0")" || exit 1

PORT="${1:-8000}"
LANIP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)"
echo "───────────────────────────────────────────────"
echo "  MyMoney → http://localhost:${PORT}"
[ -n "$LANIP" ] && echo "  En la red local → http://${LANIP}:${PORT}"
echo "  Usuario: angelgbct@gmail.com  ·  Contraseña: finanzas123"
[ -n "$DATABASE_URL" ] && echo "  Base de datos: Neon/Postgres (DATABASE_URL)" || echo "  Base de datos: SQLite local (finance.db)"
echo "  (Ctrl+C para parar)"
echo "───────────────────────────────────────────────"
# --host 0.0.0.0 permite acceder también desde otros dispositivos en la misma WiFi.
exec python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT}"
