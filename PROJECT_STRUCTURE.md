# Project structure

```text
mikrotik_dashboard/
├── streamlit_app.py              # Router multipage dan inisialisasi aplikasi
├── app_pages/                    # UI per halaman Streamlit
│   ├── home.py
│   ├── crew.py
│   ├── devices.py
│   ├── access_points.py
│   ├── bandwidth.py
│   ├── internet_plan.py
│   ├── quota.py
│   ├── transactions.py
│   ├── analytics.py
│   ├── forecast.py
│   ├── alerts.py
│   ├── reports.py
│   ├── firewall.py
│   ├── logs.py
│   ├── security.py
│   └── settings.py
├── config/                       # Konfigurasi aplikasi dan environment
├── database/                     # SQLite connection, schema, dan initial dataset
├── quota/                        # Business rules quota, allocation, alert, forecast
├── mikrotik/                     # Adapter RouterOS: connection, users, traffic, firewall, AP
├── utils/                        # Formatter dan validator bersama
├── data/
│   ├── database/                 # File SQLite lokal
│   ├── exports/                  # CSV, Excel, PDF
│   └── backups/                  # Backup database
├── tests/                        # Unit test business logic
├── .streamlit/                   # Theme dan konfigurasi Streamlit
├── requirements.txt
├── .env.example
├── README.md
├── PROJECT_STRUCTURE.md
└── ROADMAP.md
```

`app_pages/` sengaja digunakan sebagai pengganti folder `pages/` agar navigasi memakai `st.navigation` dan tidak bercampur dengan auto-discovery legacy Streamlit.
