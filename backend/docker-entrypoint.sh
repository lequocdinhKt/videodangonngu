#!/bin/sh
set -e

case "$1" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    exec arq app.workers.arq_worker.WorkerSettings
    ;;
  *)
    exec "$@"
    ;;
esac
