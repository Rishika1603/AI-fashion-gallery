#!/bin/sh
# Root-level entry point. The Dockerfile build ignores this and runs
# backend/start.sh directly inside the container. This file exists so
# Railway's Railpack auto-detect builder can find a start script when
# the service is configured for auto-detection.
cd "$(dirname "$0")/backend" || exit 1
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
