#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/mikrotik_dashboard"
SERVICE_NAME="mikrotik-dashboard"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo bash deploy/vps/install_ubuntu.sh"
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx git

mkdir -p "$APP_DIR"
rsync -a --delete ./ "$APP_DIR"/

cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp deploy/vps/env.production.example .env
  echo "Created .env from template. Please edit credentials before starting service."
fi

cp deploy/vps/mikrotik-dashboard.service /etc/systemd/system/${SERVICE_NAME}.service
cp deploy/vps/nginx-mikrotik-dashboard.conf /etc/nginx/sites-available/${SERVICE_NAME}
ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
systemctl restart nginx

echo "Install complete."
echo "Next: edit $APP_DIR/.env if needed, then run: systemctl restart ${SERVICE_NAME}"
