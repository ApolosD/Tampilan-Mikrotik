# Deploy to VPS (Production)

Dokumen ini untuk memastikan aplikasi Streamlit tidak sleep dan startup lebih stabil di server.

## 1) Jalankan app sebagai service systemd

Contoh service file:

```ini
[Unit]
Description=MikroTik Dashboard Streamlit
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mikrotik_dashboard
EnvironmentFile=/opt/mikrotik_dashboard/.env
ExecStart=/opt/mikrotik_dashboard/.venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=3
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
```

Simpan sebagai `/etc/systemd/system/mikrotik-dashboard.service` lalu:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mikrotik-dashboard
sudo systemctl restart mikrotik-dashboard
sudo systemctl status mikrotik-dashboard
```

## 2) Reverse proxy Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300;
    }
}
```

## 3) Hindari sleep

Jika berjalan di VPS sendiri dengan systemd, aplikasi tidak sleep selama service aktif.

Cek service:

```bash
sudo systemctl is-active mikrotik-dashboard
sudo journalctl -u mikrotik-dashboard -n 100 --no-pager
```

## 4) Health check sederhana

Tambahkan monitoring eksternal (Uptime Kuma atau sejenis) untuk hit endpoint root setiap 1-5 menit.

## 5) Optimasi startup yang sudah diterapkan di kode

- Snapshot RouterOS tidak dipanggil di setiap rerun.
- Refresh snapshot dibatasi interval pendek.
- Sinkronisasi hotspot user dibatasi interval lebih longgar.
- Konfigurasi Streamlit production: `runOnSave=false`, `fileWatcherType=none`, `fastReruns=true`.
