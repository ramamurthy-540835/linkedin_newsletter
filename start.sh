#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Post Generator — startup script
#
# Usage:
#   ./start.sh                   # use defaults (backend 8001, frontend 3000)
#   ./start.sh 8002 3001         # custom ports
#   ./start.sh --kill-only       # just kill whatever is on the default ports
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configurable ports ────────────────────────────────────────────────────────
BACKEND_PORT="${1:-8001}"
FRONTEND_PORT="${2:-3000}"

# Handle --kill-only flag
if [[ "${1:-}" == "--kill-only" ]]; then
  BACKEND_PORT=8001
  FRONTEND_PORT=3000
  KILL_ONLY=true
else
  KILL_ONLY=false
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV="$SCRIPT_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/.logs"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}▸${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET} $*"; }
error()   { echo -e "${RED}✗${RESET} $*"; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

# ── Kill process on a port ─────────────────────────────────────────────────────
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    success "Killed process(es) on port $port"
  else
    info "Port $port is already free"
  fi
}

# ── Detect host IP for URL display ────────────────────────────────────────────
get_host_ip() {
  # Try common methods; fall back to localhost
  hostname -I 2>/dev/null | awk '{print $1}' \
    || ip route get 1 2>/dev/null | awk '{print $7; exit}' \
    || echo "localhost"
}

# ── Main ──────────────────────────────────────────────────────────────────────

header "═══ LinkedIn Post Generator ═══"

# Kill ports
header "Freeing ports…"
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

if $KILL_ONLY; then
  success "Done (kill-only mode)."
  exit 0
fi

# Validate dirs
for d in "$BACKEND_DIR" "$FRONTEND_DIR"; do
  [[ -d "$d" ]] || { error "Directory not found: $d"; exit 1; }
done

# Check venv (look in project root first, then backend/)
UVICORN=""
for candidate in "$VENV/bin/uvicorn" "$BACKEND_DIR/.venv/bin/uvicorn"; do
  if [[ -x "$candidate" ]]; then
    UVICORN="$candidate"
    break
  fi
done
if [[ -z "$UVICORN" ]]; then
  error "uvicorn not found. Expected at $VENV/bin/uvicorn or $BACKEND_DIR/.venv/bin/uvicorn"
  exit 1
fi

# Update frontend env with current ports/IP
HOST_IP=$(get_host_ip)
ENV_FILE="$FRONTEND_DIR/.env.local"
cat > "$ENV_FILE" <<EOF
NEXT_PUBLIC_API_BASE_URL=http://${HOST_IP}:${BACKEND_PORT}/api
NEXT_PUBLIC_APP_URL=http://${HOST_IP}:${FRONTEND_PORT}
NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}
EOF
success "Updated $ENV_FILE"

# Create log dir
mkdir -p "$LOG_DIR"

# ── Start backend ─────────────────────────────────────────────────────────────
header "Starting backend (port $BACKEND_PORT)…"
(
  cd "$BACKEND_DIR"
  "$UVICORN" app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    >> "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$LOG_DIR/backend.pid"
)
BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
success "Backend started (PID $BACKEND_PID) → log: .logs/backend.log"

# Wait briefly for backend to come up
sleep 2
if kill -0 "$BACKEND_PID" 2>/dev/null; then
  success "Backend is running"
else
  error "Backend failed to start. Check .logs/backend.log"
  cat "$LOG_DIR/backend.log" | tail -20
  exit 1
fi

# ── Start frontend ────────────────────────────────────────────────────────────
header "Starting frontend (port $FRONTEND_PORT)…"
(
  cd "$FRONTEND_DIR"
  rm -rf .next .turbo
  npm run dev -- -p "$FRONTEND_PORT" \
    >> "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$LOG_DIR/frontend.pid"
)
FRONTEND_PID=$(cat "$LOG_DIR/frontend.pid")
success "Frontend started (PID $FRONTEND_PID) → log: .logs/frontend.log"

# Wait for Next.js to be ready
info "Waiting for frontend to be ready…"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✓ LinkedIn Post Generator is running!${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Frontend${RESET}  →  ${CYAN}http://${HOST_IP}:${FRONTEND_PORT}${RESET}"
echo -e "  ${BOLD}Backend ${RESET}  →  ${CYAN}http://${HOST_IP}:${BACKEND_PORT}${RESET}"
echo -e "  ${BOLD}API docs${RESET}  →  ${CYAN}http://${HOST_IP}:${BACKEND_PORT}/docs${RESET}"
echo ""
echo -e "  Logs:  .logs/backend.log   .logs/frontend.log"
echo -e "  Stop:  ${YELLOW}./start.sh --kill-only${RESET}   or   ${YELLOW}Ctrl+C${RESET}"
echo ""

# ── Tail logs (Ctrl+C to exit) ────────────────────────────────────────────────
cleanup() {
  echo ""
  warn "Shutting down…"
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
  success "Stopped."
  exit 0
}
trap cleanup INT TERM

tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
