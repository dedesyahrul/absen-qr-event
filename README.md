# Absen QR Vendor Gathering

Environment awal untuk sistem absensi QR event dengan:

- Backend: Python 3.12 + FastAPI
- Frontend: Vue 3 + Vite
- Database: PostgreSQL 16
- Orkestrasi: Docker Compose

## Deployment

Deployment production tersedia melalui `regist.dedesyahrul.dev` dengan Docker Compose, Caddy, dan HTTPS otomatis.

Panduan lengkap ada di [`DOCKER.md`](DOCKER.md).

Port internal container PostgreSQL tetap `5432`, backend `8000`, dan frontend `80`. Port tersebut hanya digunakan di jaringan internal Docker.

## Menjalankan Environment

1. Buat file environment:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Isi `POSTGRES_PASSWORD`, `JWT_SECRET`, dan `ACME_EMAIL` pada `.env`.

3. Pastikan DNS `regist.dedesyahrul.dev` sudah mengarah ke IP server, lalu jalankan service:

   ```powershell
   docker compose up --build
   ```

4. Buka frontend pada `https://regist.dedesyahrul.dev`.

5. Periksa health API pada `https://regist.dedesyahrul.dev/api/health`.

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

## Catatan Pengembangan

## Fitur yang Sudah Berfungsi

- Login admin dengan JWT.
- Seed akun development: `admin@example.com` / `admin123`.
- Seed event, vendor, dan peserta pertama kali database dibuat.
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
