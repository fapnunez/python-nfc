#!/bin/sh
set -eu

PORT="${PORT:-5003}"
exec python -m gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  app:app
