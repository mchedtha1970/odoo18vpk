#!/usr/bin/env bash
# Open the maintenance app in the iPhone Simulator via Expo Go.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${1:-8082}"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin:${PATH:-}"
ulimit -n 10240 2>/dev/null || true

kill_port() {
  for pid in $(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true); do
    kill -9 "$pid" 2>/dev/null || true
  done
  pkill -f "expo start --go --localhost --port ${PORT}" 2>/dev/null || true
  pkill -f "ipv4-metro-proxy.sh ${PORT}" 2>/dev/null || true
  sleep 1
}

wait_http() {
  local url="$1" tries="${2:-40}"
  for _ in $(seq 1 "$tries"); do
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 "$url" | grep -q "200"; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

kill_port

echo "Starting Metro on localhost:${PORT}..."
nohup npx expo start --go --localhost --port "$PORT" > /tmp/vpk-ma-metro.log 2>&1 &
echo $! > /tmp/vpk-ma-metro.pid

if ! wait_http "http://[::1]:${PORT}/status" 60 && ! wait_http "http://127.0.0.1:${PORT}/status" 5; then
  echo "Metro failed to start. Log:"
  tail -50 /tmp/vpk-ma-metro.log || true
  exit 1
fi

if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 "http://127.0.0.1:${PORT}/status" | grep -q "200"; then
  echo "Metro already reachable on 127.0.0.1"
else
  echo "Starting IPv4 proxy 127.0.0.1 -> [::1]..."
  nohup bash "$ROOT/scripts/ipv4-metro-proxy.sh" "$PORT" > /tmp/vpk-ma-proxy.log 2>&1 &
  echo $! > /tmp/vpk-ma-proxy.pid
  if ! wait_http "http://127.0.0.1:${PORT}/status" 20; then
    echo "Proxy failed. Log:"
    cat /tmp/vpk-ma-proxy.log || true
    exit 1
  fi
fi

open -a Simulator
BOOTED="$(xcrun simctl list devices booted | grep -c Booted || true)"
if [ "$BOOTED" = "0" ]; then
  DEVICE="$(xcrun simctl list devices available | grep -E 'iPhone' | head -1 | sed -E 's/.*\(([A-F0-9-]+)\).*/\1/')"
  xcrun simctl boot "$DEVICE" || true
  sleep 2
fi
xcrun simctl launch booted host.exp.Exponent >/dev/null 2>&1 || true
sleep 1
xcrun simctl openurl booted "exp://127.0.0.1:${PORT}"
echo "Opened exp://127.0.0.1:${PORT}"
