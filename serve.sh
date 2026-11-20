#!/usr/bin/env bash
# Локальная раздача приложения «Подарки» по Wi-Fi.
# Запуск: ./serve.sh   (остановить — Ctrl+C)
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"

lan_ip() {
  local iface addr
  for iface in en0 en1; do
    addr="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
    if [ -n "$addr" ]; then
      printf '%s' "$addr"
      return 0
    fi
  done
  return 1
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "Не найден python3. Установите Python 3 и повторите." >&2
  exit 1
fi

IP="$(lan_ip || true)"
LINE="$(printf '═%.0s' $(seq 1 46))"

url_box() {
  printf '╔%s╗\n' "$LINE"
  printf '║   %-40s   ║\n' "$1"
  printf '╚%s╝\n' "$LINE"
}

printf '\n'
printf 'ПОДАРКИ · локальный сервер · порт %s\n\n' "$PORT"

if [ -n "$IP" ]; then
  printf 'На iPhone в той же Wi-Fi открой в Safari:\n\n'
  url_box "http://$IP:$PORT"
else
  printf 'IP не определён (Wi-Fi выключен?).\n'
  printf 'Для iPhone включи Wi-Fi и перезапусти скрипт.\n'
fi

printf '\nНа этом Mac:\n\n'
url_box "http://localhost:$PORT"
printf '\nCtrl+C — остановить сервер.\n\n'

exec python3 -m http.server "$PORT" --bind 0.0.0.0
