#!/bin/sh
set -e

case "$1" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
  *)
    exec "$@"
    ;;
esac
