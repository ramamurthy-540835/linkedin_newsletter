#!/usr/bin/env bash

# LinkedIn Newsletter App - Start/Stop/Manage Script
# Manages starting and stopping the frontend (port 3007) and backend (port 8007)

set -e

# Configuration
FRONTEND_PORT=3007
BACKEND_PORT=8007
HOST_IP=10.100.15.27
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to print colored output
print_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Show help
show_help() {
  cat << EOF
LinkedIn Newsletter App - Start/Stop Manager

Usage: ./start.sh [COMMAND]

Commands:
  start           Start both frontend and backend (default)
  stop            Stop both frontend and backend
  restart         Restart both frontend and backend
  status          Check status of both services
  kill-all        Force kill all processes on ports ${FRONTEND_PORT} and ${BACKEND_PORT}
  help            Show this help message

Ports:
  Frontend: ${FRONTEND_PORT}
  Backend:  ${BACKEND_PORT}

Examples:
  ./start.sh              # Start services
  ./start.sh stop         # Stop services
  ./start.sh restart      # Restart services
  ./start.sh status       # Check status

EOF
}

# Kill process on a specific port (robust version using ss)
kill_port() {
  local port=$1
  local max_retries=5
  local retry=0

  while [ $retry -lt $max_retries ]; do
    # Try ss first (most reliable on Linux)
    if command -v ss &>/dev/null; then
      local pids=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oE 'pid=[0-9]+' | cut -d= -f2) || true
      if [ -n "$pids" ]; then
        echo "$pids" | while read pid; do
          kill -9 "$pid" 2>/dev/null || true
        done
      fi
    fi

    # Try fuser as fallback
    if command -v fuser &>/dev/null; then
      fuser -k $port/tcp 2>/dev/null || true
    fi

    # Try lsof as last fallback
    if command -v lsof &>/dev/null; then
      local pids=$(lsof -ti:${port} 2>/dev/null || echo "")
      if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
      fi
    fi

    # Check if port is actually released
    if ! timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
      return 0
    fi

    retry=$((retry + 1))
    if [ $retry -lt $max_retries ]; then
      sleep 1
    fi
  done

  sleep 1
}

# Wait for port to become available
wait_port_available() {
  local port=$1
  local timeout=${2:-10}
  local elapsed=0

  while [ $elapsed -lt $timeout ]; do
    if ! timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
    elapsed=$((elapsed + 1))
  done

  return 1
}

# Wait for backend HTTP health endpoint
wait_backend_ready() {
  local timeout=${1:-20}
  local elapsed=0

  while [ $elapsed -lt $timeout ]; do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        return 0
      fi
    else
      if timeout 1 bash -c "echo > /dev/tcp/localhost/${BACKEND_PORT}" 2>/dev/null; then
        return 0
      fi
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

# Kill all processes (frontend and backend)
kill_all() {
  print_info "Force killing all services..."
  kill_port ${BACKEND_PORT}
  kill_port ${FRONTEND_PORT}
  print_success "All services killed"
}

# Check status of services
check_status() {
  print_info "Checking service status..."

  local backend_running=false
  local frontend_running=false

  if timeout 2 bash -c "echo > /dev/tcp/localhost/${BACKEND_PORT}" 2>/dev/null; then
    backend_running=true
    print_success "Backend is running on port ${BACKEND_PORT}"
  else
    print_warning "Backend is NOT running on port ${BACKEND_PORT}"
  fi

  if timeout 2 bash -c "echo > /dev/tcp/localhost/${FRONTEND_PORT}" 2>/dev/null; then
    frontend_running=true
    print_success "Frontend is running on port ${FRONTEND_PORT}"
  else
    print_warning "Frontend is NOT running on port ${FRONTEND_PORT}"
  fi

  echo ""
  if [ "$backend_running" = true ] && [ "$frontend_running" = true ]; then
    print_success "Both services are running"
    return 0
  else
    print_warning "One or more services are not running"
    return 1
  fi
}

# Stop services
stop_services() {
  print_info "Stopping services..."

  kill_port ${BACKEND_PORT}
  kill_port ${FRONTEND_PORT}

  print_success "Services stopped"
}

# Cleanup function for graceful shutdown
cleanup() {
  print_warning "Shutting down services gracefully..."
  stop_services
  exit 0
}

# Set up trap for Ctrl+C
trap cleanup SIGINT SIGTERM

# Start services
start_services() {
  print_info "Starting LinkedIn Newsletter App..."
  echo ""

  # Kill existing processes
  print_info "Cleaning up existing processes..."
  kill_port ${BACKEND_PORT}
  kill_port ${FRONTEND_PORT}

  # Start Backend
  print_info "Starting Backend service..."

  if [ ! -d "${BACKEND_DIR}" ]; then
    print_error "Backend directory not found at ${BACKEND_DIR}"
    return 1
  fi

  # Create venv if it doesn't exist
  if [ ! -d "${BACKEND_DIR}/venv" ]; then
    print_info "Creating Python virtual environment..."
    cd "${BACKEND_DIR}"
    python3 -m venv venv
    cd "${PROJECT_ROOT}"
  fi

  # Activate venv and install requirements
  cd "${BACKEND_DIR}"
  source venv/bin/activate

  if [ -f "requirements.txt" ]; then
    print_info "Installing backend dependencies..."
    pip install -q -r requirements.txt || {
      print_error "Failed to install backend dependencies"
      return 1
    }
  fi

  # Start backend in background
  PYTHONUNBUFFERED=1 python -m uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > "${PROJECT_ROOT}/.logs/backend.log" 2>&1 &
  local backend_pid=$!

  cd "${PROJECT_ROOT}"

  print_info "Backend PID: ${backend_pid}"

  # Wait for backend to be ready
  print_info "Waiting for backend to start (5 seconds)..."
  sleep 5

  # Verify backend is running using health endpoint
  if ! wait_backend_ready 25; then
    print_error "Backend failed to start. Check logs at ${PROJECT_ROOT}/.logs/backend.log"
    cat "${PROJECT_ROOT}/.logs/backend.log" 2>/dev/null | tail -10 || true
    return 1
  fi

  print_success "Backend started successfully on port ${BACKEND_PORT}"
  echo ""

  # Start Frontend
  print_info "Starting Frontend service..."

  if [ ! -d "${FRONTEND_DIR}" ]; then
    print_error "Frontend directory not found at ${FRONTEND_DIR}"
    return 1
  fi

  cd "${FRONTEND_DIR}"

  # Install node_modules if needed
  if [ ! -d "node_modules" ]; then
    print_info "Installing frontend dependencies..."
    npm install || {
      print_error "Failed to install frontend dependencies"
      return 1
    }
  fi

  # Update .env.local
  print_info "Configuring frontend environment..."
  if [ ! -f ".env.local" ]; then
    touch .env.local
  fi

  # Pin backend URL to the shared host/IP used by this workspace.
  if grep -q "NEXT_PUBLIC_API_URL" .env.local; then
    sed -i "s|.*NEXT_PUBLIC_API_URL.*|NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}|g" .env.local
  else
    echo "NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}" >> .env.local
  fi

  # Wait for port to be available before starting frontend
  sleep 2
  if ! wait_port_available ${FRONTEND_PORT} 5; then
    print_warning "Port ${FRONTEND_PORT} still in use, forcing cleanup..."
    kill_port ${FRONTEND_PORT}
    sleep 2
  fi

  # Start frontend with explicit port flag
  npm run dev -- -p ${FRONTEND_PORT} > "${PROJECT_ROOT}/.logs/frontend.log" 2>&1 &
  local frontend_pid=$!

  cd "${PROJECT_ROOT}"

  print_info "Frontend PID: ${frontend_pid}"

  # Wait for frontend to be ready
  print_info "Waiting for frontend to start (10 seconds)..."
  sleep 10

  # Verify frontend is running (with retries)
  local frontend_retry=0
  while [ $frontend_retry -lt 3 ]; do
    if timeout 3 bash -c "echo > /dev/tcp/localhost/${FRONTEND_PORT}" 2>/dev/null; then
      break
    fi
    frontend_retry=$((frontend_retry + 1))
    if [ $frontend_retry -lt 3 ]; then
      print_warning "Frontend port check failed, retrying... (${frontend_retry}/2)"
      sleep 2
    fi
  done

  if [ $frontend_retry -eq 3 ]; then
    print_error "Frontend failed to start. Check logs at ${PROJECT_ROOT}/.logs/frontend.log"
    cat "${PROJECT_ROOT}/.logs/frontend.log" 2>/dev/null | tail -20 || true
    return 1
  fi

  print_success "Frontend started successfully on port ${FRONTEND_PORT}"
  echo ""

  # Print summary
  print_success "All services started successfully!"
  echo ""
  print_info "Frontend: http://${HOST_IP}:${FRONTEND_PORT}"
  print_info "Backend:  http://${HOST_IP}:${BACKEND_PORT}"
  print_info "Logs:"
  print_info "  Backend:  ${PROJECT_ROOT}/.logs/backend.log"
  print_info "Frontend: ${PROJECT_ROOT}/.logs/frontend.log"
  echo ""
  print_info "Press Ctrl+C to stop all services"
  echo ""

  # Wait for both processes
  wait $backend_pid $frontend_pid 2>/dev/null || true
}

# Main script logic
main() {
  local command="${1:-start}"

  case "$command" in
    start)
      start_services
      ;;
    stop)
      stop_services
      ;;
    restart)
      stop_services
      echo ""
      start_services
      ;;
    status)
      check_status
      ;;
    kill-all)
      kill_all
      ;;
    help)
      show_help
      ;;
    *)
      print_error "Unknown command: $command"
      echo ""
      show_help
      exit 1
      ;;
  esac
}

# Run main function
main "$@"
