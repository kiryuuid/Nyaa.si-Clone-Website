# NyaaMirror — Nyaa.si Clone

Website torrent yang mengambil data dari nyaa.si, dibangun dengan Python (Flask) dan Tailwind CSS.

## 🚀 Cara Menjalankan

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Jalankan server
```bash
python app.py
```

### 3. Buka browser
```
http://localhost:5000
```

## 📁 Struktur Proyek
```
nyaa-clone/
├── app.py              # Backend Flask utama
├── requirements.txt    # Python dependencies
├── templates/
│   ├── base.html       # Layout dasar
│   ├── index.html      # Halaman pencarian & daftar torrent
│   ├── detail.html     # Halaman detail torrent
│   └── error.html      # Halaman error
└── static/             # Static assets (opsional)
```

## ✨ Fitur
- 🔍 **Search** — Cari torrent dari nyaa.si secara real-time
- 📂 **Filter Kategori** — Anime, Audio, Literature, Live Action, Pictures, Software
- 🛡️ **Filter Status** — No Filter, No Remakes, Trusted Only
- 📄 **Pagination** — Navigasi halaman
- 🔗 **Download** — Link .torrent dan magnet langsung
- 📋 **Detail View** — Info lengkap, daftar file, deskripsi, komentar
- 📡 **RSS Proxy** — Endpoint /rss untuk RSS feed

## 🛠️ Teknologi
- **Backend**: Python 3 + Flask
- **Scraping**: requests + BeautifulSoup4
- **Frontend**: Jinja2 Templates + Tailwind CSS (CDN)
- **Font**: JetBrains Mono + Zen Kaku Gothic Antique

## ⚠️ Catatan
- Pastikan koneksi internet aktif (data diambil langsung dari nyaa.si)
- Kecepatan bergantung pada response time nyaa.si
- Untuk production, pertimbangkan menggunakan caching (Redis/memcache)
