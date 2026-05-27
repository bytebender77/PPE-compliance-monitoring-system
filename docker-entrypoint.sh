#!/usr/bin/env bash
# docker-entrypoint.sh — Route to the right Python module
set -e

MODE="${1:-api}"
shift || true   # remaining args passed through

case "$MODE" in
  pipeline)
    exec python -m ppe_compliance_system.main "$@"
    ;;
  api)
    exec python -m ppe_compliance_system.api "$@"
    ;;
  multi)
    exec python -m ppe_compliance_system.multi_main "$@"
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Usage: docker run ppe-compliance [pipeline|api|multi] [args...]"
    exit 1
    ;;
esac
