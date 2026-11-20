#!/bin/bash
# Локальный запуск приложения в прод-режиме: подарки открываются по датам.
# Двойной клик по этому файлу в Finder.
cd "$(dirname "$0")" || exit 1

PORT="${PORT:-8000}"
URL="http://localhost:$PORT/"

echo ""
echo "  ЛОКАЛЬНЫЙ ЗАПУСК — подарки открываются по своим датам"
echo "  ---------------------------------------------------"
echo "  На этом Mac :  $URL"

LAN=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
if [ -n "$LAN" ]; then
  echo "  На iPhone   :  http://$LAN:$PORT"
  echo "               (телефон должен быть в той же Wi-Fi)"
fi

echo ""
echo "  Остановить сервер: Ctrl+C"
echo ""

( sleep 1; open "$URL" ) &
exec python3 -m http.server "$PORT" --bind 0.0.0.0
