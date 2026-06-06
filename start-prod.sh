#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
BACKEND_PORT=8000

echo "==> AAOS production start"
echo "    Public port : $PORT"
echo "    Backend port: $BACKEND_PORT"

# Create nginx temp dirs (runs without root)
mkdir -p /tmp/nginx-client-body /tmp/nginx-proxy \
         /tmp/nginx-fastcgi /tmp/nginx-uwsgi /tmp/nginx-scgi

# Inject runtime port into nginx config
sed "s/__PORT__/$PORT/" /app/nginx.conf > /tmp/nginx-runtime.conf

# Ensure workspace + log dirs exist
mkdir -p /app/workspace /app/logs

# ── Start backend (uvicorn) ────────────────────────────────────────────────
echo "==> Starting backend on port $BACKEND_PORT ..."
uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "$BACKEND_PORT" \
  --log-level info \
  --workers 1 &
BACKEND_PID=$!

# Wait until backend is ready (max 30 s)
echo "==> Waiting for backend to be ready ..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo "==> Backend ready after ${i}s"
    break
  fi
  sleep 1
done

# ── Start nginx (serves React SPA + proxies API/WS) ───────────────────────
echo "==> Starting nginx on port $PORT ..."
nginx -c /tmp/nginx-runtime.conf -g "daemon off;" &
NGINX_PID=$!

echo "==> AAOS running"
echo "    Frontend : http://0.0.0.0:$PORT"
echo "    API Docs : http://0.0.0.0:$PORT/api/v1/docs"
echo "    WebSocket: ws://0.0.0.0:$PORT/ws/events"

# Trap SIGTERM/SIGINT and shut both processes down cleanly
_shutdown() {
  echo "==> Shutting down ..."
  kill "$NGINX_PID"   2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  wait
  echo "==> Done."
}
trap _shutdown TERM INT

# Wait for either process to exit; restart on unexpected exit
while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[WARN] Backend exited unexpectedly — restarting ..."
    uvicorn app.main:app \
      --host 127.0.0.1 \
      --port "$BACKEND_PORT" \
      --log-level info \
      --workers 1 &
    BACKEND_PID=$!
  fi
  if ! kill -0 "$NGINX_PID" 2>/dev/null; then
    echo "[WARN] nginx exited unexpectedly — restarting ..."
    nginx -c /tmp/nginx-runtime.conf -g "daemon off;" &
    NGINX_PID=$!
  fi
  sleep 5
done
