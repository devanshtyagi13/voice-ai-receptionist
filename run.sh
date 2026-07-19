#!/usr/bin/env bash
# One-command startup: loads .env, seeds DB if needed, starts the backend

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Activate venv
source "$ROOT/.venv/bin/activate"

# Load .env
if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | xargs)
fi

# Seed database if empty
python3 "$ROOT/scripts/seed_data.py"

# Start backend
cd "$ROOT/backend"
echo ""
echo "🚀  Starting backend on http://localhost:8000"
echo "📖  API docs: http://localhost:8000/docs"
echo "📊  Monitoring: http://localhost:8000/monitoring/summary"
echo ""
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
