#!/usr/bin/env bash
set -euo pipefail

UI_PORT="${UI_PORT:-${1:-5500}}"
BACKEND_BASE="${BACKEND_BASE:-${2:-http://127.0.0.1:8000}}"
LAT="${LAT:-${3:-}}"
LNG="${LNG:-${4:-}}"
HEADING="${HEADING:-${5:-120}}"
SESSION="${SESSION:-${6:-}}"

if [[ -z "$LAT" || -z "$LNG" ]]; then
  echo "LAT and LNG are required (env or positional args)." >&2
  exit 1
fi

urlencode() {
  python - <<'PY' "$1"
import urllib.parse, sys
print(urllib.parse.quote(sys.argv[1], safe=""))
PY
}

API_BASE_ENC="$(urlencode "$BACKEND_BASE")"
QUERY="autostart=1&lat=${LAT}&lng=${LNG}&heading=${HEADING}&apiBase=${API_BASE_ENC}"
if [[ -n "${PITCH:-}" ]]; then
  QUERY="${QUERY}&pitch=${PITCH}"
fi
if [[ -n "${FOV:-}" ]]; then
  QUERY="${QUERY}&fov=${FOV}"
fi
if [[ -n "$SESSION" ]]; then
  QUERY="${QUERY}&session=$(urlencode "$SESSION")"
fi

URL="http://127.0.0.1:${UI_PORT}/index.html?${QUERY}"

if [[ -n "${CHROME_BIN:-}" ]]; then
  CHROME="$CHROME_BIN"
elif command -v google-chrome >/dev/null 2>&1; then
  CHROME="google-chrome"
elif command -v chromium >/dev/null 2>&1; then
  CHROME="chromium"
elif command -v chromium-browser >/dev/null 2>&1; then
  CHROME="chromium-browser"
elif command -v chrome >/dev/null 2>&1; then
  CHROME="chrome"
else
  echo "Chrome/Chromium not found. Set CHROME_BIN." >&2
  exit 1
fi

CHROME_ARGS=(
  --headless=new
  --disable-gpu
  --disable-dev-shm-usage
  --window-size=1280,720
  --user-data-dir=/tmp/chrome-profile
)

if [[ "${NO_SANDBOX:-1}" = "1" ]]; then
  CHROME_ARGS+=(--no-sandbox)
fi

echo "Opening: $URL"
exec "$CHROME" "${CHROME_ARGS[@]}" "$URL"
