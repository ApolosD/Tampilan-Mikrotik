# MikroTik Internet & Crew Management

Dashboard Python + Streamlit untuk mengelola internet berbasis MikroTik dan Access Point. Project ini dibuat terpisah dari `Monitor Data` dan mengikuti blueprint utama.

## Status saat ini

Foundation dan dashboard utama sudah tersedia:

- Streamlit multipage navigation without a NumPy/Pandas runtime dependency
- SQLite database dan initial dataset
- Unlimited dan Limited mode dengan snapshot quota saat berpindah mode
- Mode Limited dengan master quota 500 GB
- Custom quota allocation per crew
- Actual usage vs display usage
- Auto-block rule pada threshold 80%
- Crew dashboard
- Internet plan
- Quota transaction history
- System logs
- Access point dan device mapping
- Bandwidth monitoring
- Usage analytics dan forecast
- Alerts dan firewall readiness
- Security role matrix
- CSV, Excel, dan PDF reports
- MikroTik connection status and credential validation
- Test untuk quota engine

## Menjalankan

Dari folder `mikrotik_dashboard`:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.port 8501
```

Database lokal otomatis dibuat di `data/database/mikrotik_dashboard.db` saat aplikasi pertama kali dijalankan.

## Konfigurasi MikroTik

### Local RouterOS connection

GitHub tidak diperlukan untuk menjalankan atau menguji aplikasi. Salin `.env.example` menjadi `.env`, lalu isi:

```text
MIKROTIK_HOST=192.168.88.1
MIKROTIK_PORT=8728
MIKROTIK_USER=dashboard_reader
MIKROTIK_PASS=your-password
```

Di MikroTik, aktifkan service API pada port yang dipilih dan gunakan user khusus dengan permission minimum untuk monitoring. Setelah aplikasi berjalan, buka **Settings**, lalu tekan **Test MikroTik connection**. Overview akan membaca RouterOS resource dan sesi Hotspot aktif ketika status koneksi `ONLINE`.

Jangan commit `.env`. GitHub hanya opsional untuk version control atau backup source code.

## Validasi

```powershell
python -m pytest tests -q
python -m compileall -q .
```

## Dokumen

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) menjelaskan fungsi setiap folder.
- [ROADMAP.md](ROADMAP.md) menjelaskan urutan implementasi blueprint.
- [../Blueprint Project.txt](../Blueprint%20Project.txt) adalah baseline kebutuhan asli.

## Prinsip domain

Nilai `actual_used_gb` dan `actual_usage_percentage` tidak dimanipulasi untuk UI. Ketika user mencapai threshold blocking, `display_usage_percentage` menjadi 100 dan status menjadi `BLOCKED`, sedangkan data aktual tetap disimpan.
