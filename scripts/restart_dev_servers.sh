#!/usr/bin/env bash
set -euo pipefail

# Stops anything bound to the dev ports, then launches backend and frontend.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_LOG="${BACKEND_LOG:-${ROOT_DIR}/backend/devserver.log}"
FRONTEND_LOG="${FRONTEND_LOG:-${ROOT_DIR}/frontend/devserver.log}"

BACKEND_CMD=(
  "${ROOT_DIR}/backend/venv/bin/python"
  "${ROOT_DIR}/backend/manage.py"
  "runserver"
  "0.0.0.0:${BACKEND_PORT}"
)

FRONTEND_CMD=(
  npm
  --prefix "${ROOT_DIR}/frontend"
  run dev --
  --host
  --port "${FRONTEND_PORT}"
)

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)

  if [[ -z "${pids}" ]]; then
    echo "No process listening on port ${port}"
    return
  fi

  echo "Stopping processes on port ${port}: ${pids}"
  kill ${pids} 2>/dev/null || true
  sleep 1

  local survivors
  survivors=$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "${survivors}" ]]; then
    echo "Force killing remaining processes on port ${port}: ${survivors}"
    kill -9 ${survivors} 2>/dev/null || true
  fi
}

start_backend() {
  echo "Starting backend server on port ${BACKEND_PORT} (log: ${BACKEND_LOG})"
  (cd "${ROOT_DIR}/backend" && "${BACKEND_CMD[@]}") >"${BACKEND_LOG}" 2>&1 &
  echo "Backend PID: $!"
}

start_frontend() {
  echo "Starting frontend dev server on port ${FRONTEND_PORT} (log: ${FRONTEND_LOG})"
  (cd "${ROOT_DIR}/frontend" && "${FRONTEND_CMD[@]}") >"${FRONTEND_LOG}" 2>&1 &
  echo "Frontend PID: $!"
}

kill_port "${BACKEND_PORT}"
kill_port "${FRONTEND_PORT}"

start_backend
start_frontend

echo "Servers started. Tail logs with:"
echo "  tail -f \"${BACKEND_LOG}\""
echo "  tail -f \"${FRONTEND_LOG}\""
