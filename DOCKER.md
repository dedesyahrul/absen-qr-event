# Docker Deployment

Deployment production untuk aplikasi ini menggunakan Docker Compose dengan:

- PostgreSQL 16, hanya tersedia di jaringan internal Docker.
- FastAPI backend, hanya tersedia di jaringan internal Docker.
- Vue frontend yang dibuild menjadi static files dan dilayani Nginx internal.
- Caddy dari project `dedesyahrul-portfolio` sebagai reverse proxy publik dengan HTTPS Let's Encrypt otomatis.

Jika VPS sudah memiliki Caddy publik dari project lain, gunakan Caddy tersebut
sebagai reverse proxy utama. Service `proxy` pada Compose ini memiliki profile
`standalone` sehingga tidak ikut dijalankan oleh `docker compose up` biasa.

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

## Jalankan Dengan Caddy Existing

Buat network bersama dan hubungkan Caddy publik yang sudah ada. Nama container
di bawah mengikuti server Anda:

```bash
docker network inspect public_proxy >/dev/null 2>&1 || docker network create public_proxy
docker network connect public_proxy dedesyahrul-portfolio 2>/dev/null || true
```

```bash
docker compose config
docker compose up -d --build db backend frontend
docker compose ps
```

Pastikan network `public_proxy` berisi `dedesyahrul-portfolio`, `absen-qr-backend`,
dan `absen-qr-frontend`. Caddy portfolio yang akan meminta sertifikat TLS.

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
docker compose up -d --build db backend frontend

# Restart aplikasi
docker compose restart backend frontend

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

Backend, frontend, dan database tidak dipublish langsung ke host. Caddy dari
project `dedesyahrul-portfolio` tetap menjadi satu-satunya service yang membuka
port `80` dan `443`.

Tambahkan site block berikut ke Caddyfile project portfolio:

```caddyfile
regist.dedesyahrul.dev {
    handle /api/* {
        reverse_proxy absen-qr-backend:8000
    }

    handle /docs* {
        reverse_proxy absen-qr-backend:8000
    }

    handle /openapi.json {
        reverse_proxy absen-qr-backend:8000
    }

    handle {
        reverse_proxy absen-qr-frontend:80
    }
}
```

Setelah mengubah Caddyfile, validasi dan reload Caddy portfolio sesuai cara
project tersebut dijalankan. Container backend dan frontend dari project ini
sudah bergabung ke network `public_proxy`.

## Troubleshooting TLS

Jika sertifikat tidak terbit:

1. Pastikan `dig +short regist.dedesyahrul.dev` mengembalikan IP VPS.
2. Pastikan `dedesyahrul-portfolio` adalah service yang memiliki port 80/443.
3. Periksa `docker logs dedesyahrul-portfolio`.
4. Pastikan firewall cloud dan firewall OS mengizinkan TCP 80/443.

Untuk menguji konfigurasi Compose tanpa menjalankan container:

```bash
docker compose config
```

Untuk VPS yang tidak memiliki Caddy publik lain, gunakan fallback standalone
secara eksplisit:

```bash
docker compose --profile standalone up -d --build
```
