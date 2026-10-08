# Docker Deployment (Production)

Deployment production memakai Docker Compose dengan:

- PostgreSQL 16, hanya di jaringan internal Docker.
- FastAPI backend dan Vue frontend hanya tersedia melalui proxy.
- Nginx proxy HTTPS sebagai satu-satunya endpoint publik.

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
PUBLIC_BIND_IP=127.0.0.1
HTTPS_PORT=18443
CORS_ORIGINS=https://domain-anda.com
INITIAL_ADMIN_EMAIL=admin@domain-anda.com
INITIAL_ADMIN_PASSWORD=gunakan_password_admin_random_panjang
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

- HTTPS: domain publik yang dikonfigurasi pada proxy.
- API health: `https://domain-anda.com/api/health`

Reverse proxy host diarahkan ke `https://127.0.0.1:18443`. Port ini hanya bind ke loopback dan tidak dapat diakses langsung dari jaringan luar. Backend dan frontend tidak dipublish langsung ke host.

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
