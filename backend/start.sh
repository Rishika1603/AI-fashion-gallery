#!/bin/sh
set -e
echo "[start.sh] $(date -Iseconds) PID=$$ starting"
echo "[start.sh] PORT=${PORT:-8000} DATASET_DIR=${DATASET_DIR:-unset} AUTO_INGEST=${ENABLE_AUTO_INGEST:-0}"
echo "[start.sh] Python: $(python --version 2>&1) at $(which python)"
echo "[start.sh] CWD=$(pwd)"

export PYTHONPATH=/app
export GRPC_VERBOSITY=NONE
python -c "import sys; print('[start.sh] PYTHONPATH=', sys.path[:3])"
python -c "from backend.main import app" 2>&1 || echo "[start.sh] app import failed; continuing if CMD retries."

if [ "${ENABLE_AUTO_INGEST:-0}" = "1" ]; then
  echo "[start.sh] Auto-ingest enabled; checking dataset..."
  if [ -d "${DATASET_DIR:-/app/Clothes_Dataset}" ]; then
    echo "[start.sh] Found dataset at ${DATASET_DIR:-/app/Clothes_Dataset}"
    if [ -f "/app/backend/seed_db.py" ]; then
      echo "[start.sh] Running seed_db.py..."
      python /app/backend/seed_db.py || echo "[start.sh] seed_db.py failed"
    else
      echo "[start.sh] No seed_db.py present, skipping"
    fi
  else
    echo "[start.sh] Dataset dir missing: ${DATASET_DIR:-/app/Clothes_Dataset}"
  fi
fi

echo "[start.sh] Launching uvicorn..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
