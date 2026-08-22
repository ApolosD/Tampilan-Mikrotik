# Deploy Docker ke VPS

Panduan ini untuk deploy `mikrotik_dashboard` pakai container agar setup konsisten dan tidak sleep.

## Prasyarat VPS

- Ubuntu 22.04/24.04 (atau distro Linux setara)
- Docker Engine + Docker Compose plugin terpasang
- Port 80 dibuka di firewall (akses publik)

## 1) Clone / pull source terbaru

```bash
git clone https://github.com/ApolosD/Tampilan-Mikrotik.git
cd Tampilan-Mikrotik
```

Jika repo sudah ada:

```bash
cd Tampilan-Mikrotik
git pull
```

## 2) Siapkan file environment

Buat file `.env` dari template:

```bash
cp deploy/vps/env.production.example .env
nano .env
```

Wajib isi dengan benar:

- `ADMIN_PASSWORD`
- `MIKROTIK_HOST`
- `MIKROTIK_PORT`
- `MIKROTIK_USER`
- `MIKROTIK_PASS`

## 3) Build dan jalankan semua container (app + nginx)

```bash
docker compose up -d --build
```

Cek status:

```bash
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=50 nginx
```

Akses publik (tanpa `:8501`):

- `http://IP_VPS`

## 5) Verifikasi cepat

```bash
curl -I http://127.0.0.1
```

## 6) Operasional harian

Restart app:

```bash
docker compose restart app nginx
```

Update code + redeploy:

```bash
git pull
docker compose up -d --build
```

Lihat log realtime:

```bash
docker compose logs -f app
```

Stop semua service:

```bash
docker compose down
```

## Catatan penting

- Data lokal SQLite dipersist ke `./data` via volume bind.
- App tidak sleep selama container jalan (`restart: unless-stopped`).
- Untuk production domain + HTTPS, disarankan Nginx host-level + Certbot, atau Cloudflare Tunnel.
