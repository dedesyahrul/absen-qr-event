# Absen QR Vendor Gathering

Environment awal untuk sistem absensi QR event dengan:

- Backend: Python 3.12 + FastAPI
- Frontend: Vue 3 + Vite
- Database: PostgreSQL 16
- Orkestrasi: Docker Compose

## Port

Port host sengaja tidak menggunakan port default:

| Service | URL / Port Host |
| --- | --- |
| Frontend | `http://localhost:18082` |
| Backend API | `http://localhost:18081` |
| API docs | `http://localhost:18081/docs` |
| PostgreSQL | `localhost:55432` |

Port internal container PostgreSQL tetap `5432` dan port aplikasi tetap `8000`/`5173`. Port tersebut hanya digunakan di jaringan internal Docker.

## Menjalankan Environment

1. Buat file environment lokal:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Ubah `POSTGRES_PASSWORD` pada `.env`.

3. Jalankan seluruh service:

   ```powershell
   docker compose up --build
   ```

4. Buka frontend pada `http://localhost:18082`.

5. Periksa health API pada `http://localhost:18081/api/health`.

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
