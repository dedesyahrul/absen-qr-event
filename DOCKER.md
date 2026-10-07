# Docker Deployment

Deployment production untuk aplikasi ini menggunakan Docker Compose dengan:

- PostgreSQL 16, hanya tersedia di jaringan internal Docker.
- FastAPI backend, hanya tersedia di jaringan internal Docker.
- Vue frontend yang dibuild menjadi static files dan dilayani Nginx internal.
- Caddy sebagai reverse proxy publik dengan HTTPS Let's Encrypt otomatis.

## Prasyarat

- Docker Engine dan Docker Compose Plugin.
- VPS dengan DNS record `A` untuk `regist.dedesyahrul.dev` menuju IP VPS.
- Port TCP `80` dan `443` terbuka pada firewall VPS/cloud provider.
- Domain sudah mengarah ke VPS sebelum container dijalankan.

## Konfigurasi

Di server:

```bash
cp .env.example .env
```

Edit `.env` dan isi minimal:

```dotenv
POSTGRES_PASSWORD=gunakan_password_random_panjang
JWT_SECRET=gunakan_secret_random_panjang_lain
DOMAIN=regist.dedesyahrul.dev
ACME_EMAIL=email-untuk-notifikasi@example.com
CORS_ORIGINS=https://regist.dedesyahrul.dev
```

Generate secret dengan salah satu perintah berikut:

```bash
openssl rand -hex 32
```

Jangan commit file `.env`.

## Jalankan

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f proxy
```

Buka `https://regist.dedesyahrul.dev`. Caddy akan meminta sertifikat TLS dari Let's Encrypt secara otomatis. Proses ini membutuhkan DNS yang benar dan akses inbound ke port 80/443.

Healthcheck API dapat diperiksa dari host melalui proxy:

```bash
curl -fsS https://regist.dedesyahrul.dev/api/health
```

Swagger tersedia di `https://regist.dedesyahrul.dev/docs`.

## Operasional

```bash
# Status dan log
docker compose ps
docker compose logs --tail 100 backend

# Deploy versi terbaru
docker compose up -d --build

# Restart service
docker compose restart proxy

# Stop container tanpa menghapus data
docker compose down
```

Data PostgreSQL dan sertifikat Caddy berada pada named volume. Jangan gunakan `docker compose down -v` kecuali memang ingin menghapus database dan data TLS.

## Struktur Routing

```text
https://regist.dedesyahrul.dev/
  /             -> frontend:80
  /api/*        -> backend:8000
  /docs*        -> backend:8000
  /openapi.json -> backend:8000
```

Backend, frontend, dan database tidak dipublish langsung ke host. Hanya Caddy yang membuka port `80` dan `443`.

## Troubleshooting TLS

Jika sertifikat tidak terbit:

1. Pastikan `dig +short regist.dedesyahrul.dev` mengembalikan IP VPS.
2. Pastikan port 80 dan 443 tidak dipakai service lain.
3. Periksa `docker compose logs proxy`.
4. Pastikan firewall cloud dan firewall OS mengizinkan TCP 80/443.

Untuk menguji konfigurasi Compose tanpa menjalankan container:

```bash
docker compose config
```
