# Docker Deployment (Local)

Deployment lokal memakai Docker Compose dengan:

- PostgreSQL 16, hanya di jaringan internal Docker.
- FastAPI backend, dipublish ke host pada `127.0.0.1` saja.
- Vue frontend (static via Nginx), dipublish ke host pada `127.0.0.1` saja.
- Nginx proxy lokal dengan HTTPS self-signed pada port non-default.

Service hanya bisa diakses dari mesin lokal (`127.0.0.1`).

## Prasyarat

- Docker Engine dan Docker Compose Plugin.

## Konfigurasi

```bash
cp .env.example .env
```

Edit `.env` dan isi minimal:

```dotenv
POSTGRES_PASSWORD=gunakan_password_random_panjang
JWT_SECRET=gunakan_secret_random_panjang_lain
BACKEND_PORT=18081
FRONTEND_PORT=18082
HTTPS_PORT=18443
CORS_ORIGINS=http://127.0.0.1:18082,http://localhost:18082,https://127.0.0.1:18443,https://localhost:18443
```

Generate secret:

```bash
openssl rand -hex 32
```

Jangan commit file `.env`.

## Jalankan

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

Akses:

- HTTPS (utama): `https://127.0.0.1:18443` (sertifikat self-signed — browser akan meminta konfirmasi)
- Frontend HTTP: `http://127.0.0.1:18082`
- API health: `http://127.0.0.1:18081/api/health` atau `https://127.0.0.1:18443/api/health`
- Swagger: `https://127.0.0.1:18443/docs`

Port host bisa diganti lewat `BACKEND_PORT` / `FRONTEND_PORT` / `HTTPS_PORT` di `.env`. Binding selalu ke `127.0.0.1` (bukan `0.0.0.0`), jadi tidak terbuka ke jaringan luar.

## Operasional

```bash
# Status dan log
docker compose ps
docker compose logs --tail 100 backend

# Deploy ulang (AMAN — data tetap ada)
docker compose up -d --build

# Restart
docker compose restart backend frontend

# Stop tanpa hapus data
docker compose down
```

## Persistensi Data (penting)

Data PostgreSQL disimpan di named volume `absen-qr-event_postgres_data`.

| Perintah | Data DB |
|---|---|
| `docker compose up -d --build` | **Aman**, data tetap |
| `docker compose down` | **Aman**, data tetap |
| `docker compose down -v` | **Hapus volume = data hilang** |
| `docker volume rm ...` | **Data hilang** |

Jangan ubah `POSTGRES_PASSWORD` di `.env` setelah volume sudah dibuat. Password hanya dipakai saat volume **pertama kali** diinisialisasi. Jika diganti, backend gagal login ke DB (`password authentication failed`).

Jika sudah terlanjur beda password (tanpa menghapus volume):

```bash
docker compose exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"ALTER USER \\\"\$POSTGRES_USER\\\" WITH PASSWORD '\$POSTGRES_PASSWORD';\""
docker compose restart backend
```

Atau di PowerShell, salin script singkat `ALTER USER ... WITH PASSWORD` lewat `docker cp` lalu `docker compose exec -T db sh /tmp/fix-pg-pass.sh`.
