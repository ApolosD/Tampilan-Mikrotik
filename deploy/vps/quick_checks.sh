#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="mikrotik-dashboard"

systemctl is-active --quiet ${SERVICE_NAME} && echo "Service: active" || (echo "Service: NOT active"; exit 1)

curl -fsS http://127.0.0.1:8501 >/dev/null && echo "Local app: reachable" || (echo "Local app: not reachable"; exit 1)

nginx -t >/dev/null && echo "Nginx config: valid" || (echo "Nginx config: invalid"; exit 1)

echo "Recent service logs:"
journalctl -u ${SERVICE_NAME} -n 20 --no-pager
