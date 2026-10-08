# Absen QR Vendor Gathering

Environment awal untuk sistem absensi QR event dengan:

- Backend: Python 3.12 + FastAPI
- Frontend: Vue 3 + Vite
- Database: PostgreSQL 16
- Orkestrasi: Docker Compose

## Deployment

Deployment production memakai Docker Compose dengan reverse proxy HTTPS. Isi domain, secret, dan akun administrator pada `.env` sebelum service dijalankan.

Panduan lengkap ada di [`DOCKER.md`](DOCKER.md).

Port internal container: PostgreSQL `5432`, backend `8000`, frontend `80`. Backend dan frontend tidak dipublish langsung ke host. Proxy HTTPS hanya bind ke `127.0.0.1` pada port host non-default untuk diteruskan oleh reverse proxy domain Anda.

## Menjalankan Environment

1. Buat file environment:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Isi `POSTGRES_PASSWORD`, `JWT_SECRET`, `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`, dan `CORS_ORIGINS` pada `.env`.

3. Jalankan service:

   ```powershell
   docker compose up --build
   ```

4. Buka aplikasi pada domain HTTPS yang dikonfigurasi.

5. Periksa health API pada `https://domain-anda.com/api/health`.

Untuk menjalankan di background:

```powershell
docker compose up --build -d
```

Untuk menghentikan service:

```powershell
docker compose down
```

Untuk menghapus database development beserta volumenya:

```powershell
docker compose down -v
```

## Struktur Direktori

```text
.
├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── .env.example
└── docker-compose.yml
```


## Fitur yang Sudah Berfungsi

- Login admin dengan JWT.
- Akun administrator awal dibuat satu kali dari `INITIAL_ADMIN_EMAIL` dan `INITIAL_ADMIN_PASSWORD`.
- Dashboard event berbasis data PostgreSQL.
- Statistik total peserta, check-in, sisa peserta, dan attendance rate.
- Daftar vendor dan ringkasan kehadiran per vendor.
- Daftar peserta dengan pencarian nama, email, dan nomor telepon.
- Tambah peserta baru dengan QR token otomatis.
- Scanner QR melalui input token yang siap dihubungkan ke kamera browser.
- Check-in manual sebagai fallback.
- Proteksi check-in ganda dengan transaksi database.
- Log aktivitas check-in.
- Swagger UI untuk eksplorasi API.

## Endpoint Utama

```text
POST /api/auth/login
GET  /api/auth/me
GET  /api/events
GET  /api/events/{event_id}/dashboard
GET  /api/events/{event_id}/participants
POST /api/events/{event_id}/participants
GET  /api/events/{event_id}/vendors
POST /api/events/{event_id}/vendors
POST /api/events/{event_id}/attendance/scan
POST /api/events/{event_id}/attendance/manual
```

Catatan: tabel dibuat otomatis saat startup untuk mempercepat development. Untuk production, gunakan migration tool seperti Alembic sebelum deployment.
