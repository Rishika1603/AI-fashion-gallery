#!/bin/sh
# Defensive startup script — prints to stdout at every step so Railway
# runtime logs can show exactly where startup fails.
set -e
echo "[start.sh] $(date -Iseconds) PID=$$ starting"
echo "[start.sh] PORT=${PORT:-8000} HOST=0.0.0.0"
echo "[start.sh] Python: $(python --version 2>&1) at $(which python)"
echo "[start.sh] CWD=$(pwd) files=$(ls -la | head -20)"
echo "[start.sh] backend/ contents: $(ls -la /app/backend/ 2>&1 | head -20)"
echo "[start.sh] Importing app..."
python -c "from backend.main import app; print('[start.sh] app loaded OK:', app.title)" 2>&1
echo "[start.sh] Launching uvicorn..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
