# Deploy to VPS (Production)

Dokumen ini fokus ke deployment stabil di VPS Linux (Ubuntu 22.04/24.04), tanpa sleep, dan siap reverse proxy Nginx.

## File deploy yang disediakan

- `deploy/vps/install_ubuntu.sh`
- `deploy/vps/mikrotik-dashboard.service`
- `deploy/vps/nginx-mikrotik-dashboard.conf`
- `deploy/vps/env.production.example`
- `deploy/vps/quick_checks.sh`

## 1) Upload source ke VPS

Contoh target folder produksi:

```bash
/opt/mikrotik_dashboard
```

## 2) Jalankan installer otomatis

Di root project pada VPS:

```bash
chmod +x deploy/vps/install_ubuntu.sh deploy/vps/quick_checks.sh
sudo bash deploy/vps/install_ubuntu.sh
```

Script ini akan:

- install dependensi sistem (python3, venv, nginx)
- siapkan virtualenv dan install `requirements.txt`
- pasang service systemd
- pasang config Nginx
- restart service app dan Nginx

## 3) Isi kredensial produksi

Edit file environment:

```bash
sudo nano /opt/mikrotik_dashboard/.env
```

Minimal isi:

- `ADMIN_PASSWORD`
- `MIKROTIK_HOST`
- `MIKROTIK_PORT`
- `MIKROTIK_USER`
- `MIKROTIK_PASS`

Setelah edit:

```bash
sudo systemctl restart mikrotik-dashboard
```

## 4) Set domain Nginx

Edit:

```bash
sudo nano /etc/nginx/sites-available/mikrotik-dashboard
```

Ganti:

- `server_name your-domain.com;`

Lalu reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 5) Verifikasi cepat

```bash
sudo bash /opt/mikrotik_dashboard/deploy/vps/quick_checks.sh
```

Atau manual:

```bash
sudo systemctl status mikrotik-dashboard
curl -I http://127.0.0.1:8501
sudo journalctl -u mikrotik-dashboard -n 100 --no-pager
```

## 6) HTTPS (disarankan)

Setelah domain aktif:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Catatan sleep dan performa

- Di VPS + systemd, app tidak sleep selama service aktif.
- Kode sudah dituning untuk startup lebih ringan (snapshot/sync tidak dipanggil berlebihan per rerun).
- Config Streamlit produksi sudah diatur di `.streamlit/config.toml`.
