# Panduan Deploy Production

Dokumen ini menjelaskan build dan deployment aplikasi menggunakan Docker Compose, lalu meneruskannya ke domain publik melalui reverse proxy pada host.

## Arsitektur

```text
Internet
  |
  | https://absen.example.com
  v
Reverse proxy host (Nginx/Caddy)
  |
  | https://127.0.0.1:18443
  v
Docker proxy (Nginx)
  |-- frontend
  |-- backend
  `-- PostgreSQL
```

Hanya container `proxy` yang membuka port ke host. Port tersebut bind ke `127.0.0.1`, sedangkan backend, frontend, dan database tetap berada di jaringan internal Docker.

## Prasyarat

- Server Linux production dengan IP publik.
- DNS domain mengarah ke IP server.
- Docker Engine dan Docker Compose Plugin.
- Reverse proxy host, misalnya Nginx atau Caddy.
- Git, jika source diambil dari repository.

Contoh perintah dijalankan dari root project:

```bash
cd /opt/absen-qr-event
```

## 1. Ambil Source Code

```bash
git clone <URL_REPOSITORY> /opt/absen-qr-event
cd /opt/absen-qr-event
```

Untuk server yang sudah ter-install:

```bash
git pull --ff-only
docker compose config --quiet
docker compose up -d --build
```

Jangan commit atau mengunggah file `.env` ke repository.

## 2. Buat Environment Production

```bash
cp .env.example .env
chmod 600 .env
```

Edit `.env` dengan nilai production:

```dotenv
APP_ENV=production

POSTGRES_DB=absen_qr
POSTGRES_USER=absen
POSTGRES_PASSWORD=GANTI_DENGAN_PASSWORD_DATABASE_RANDOM

JWT_SECRET=GANTI_DENGAN_SECRET_RANDOM_MINIMAL_32_BYTE

INITIAL_ADMIN_EMAIL=admin@absen.example.com
INITIAL_ADMIN_PASSWORD=GANTI_DENGAN_PASSWORD_ADMIN_RANDOM

# Port ini hanya untuk reverse proxy pada host yang sama.
PUBLIC_BIND_IP=127.0.0.1
HTTPS_PORT=18443

# Harus sama dengan origin domain yang digunakan pengguna.
CORS_ORIGINS=https://absen.example.com
```

Generate secret random:

```bash
openssl rand -hex 32
```

`INITIAL_ADMIN_EMAIL` dan `INITIAL_ADMIN_PASSWORD` hanya digunakan untuk membuat administrator saat database belum memiliki user. Setelah login pertama, ganti password melalui menu pengaturan aplikasi.

## 3. Validasi Konfigurasi

```bash
docker compose config --quiet
```

Pastikan hanya proxy yang memiliki port host:

```bash
docker compose config | grep -A3 'ports:'
```

Mapping yang diharapkan:

```text
127.0.0.1:18443:443
```

Service `backend`, `frontend`, dan `db` tidak boleh memiliki port mapping ke host.

## 4. Build Dan Jalankan

Build image dan jalankan service di background:

```bash
docker compose up -d --build
```

Periksa status:

```bash
docker compose ps
```

Periksa log jika ada masalah:

```bash
docker compose logs --tail 100 backend
docker compose logs --tail 100 frontend
docker compose logs --tail 100 proxy
```

Periksa health endpoint dari host:

```bash
curl -k https://127.0.0.1:18443/api/health
```

Opsi `-k` digunakan karena proxy Docker menggunakan sertifikat self-signed internal. Sertifikat yang diberikan ke pengguna publik harus berasal dari reverse proxy host dengan TLS valid.

## 5. Reverse Proxy Nginx Host

Buat virtual host, misalnya `/etc/nginx/sites-available/absen.example.com`:

```nginx
server {
    listen 80;
    server_name absen.example.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name absen.example.com;

    ssl_certificate /etc/letsencrypt/live/absen.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/absen.example.com/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass https://127.0.0.1:18443;
        proxy_ssl_verify off;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;
    }
}
```

Aktifkan dan validasi konfigurasi:

```bash
sudo ln -s /etc/nginx/sites-available/absen.example.com /etc/nginx/sites-enabled/absen.example.com
sudo nginx -t
sudo systemctl reload nginx
```

Jika reverse proxy memakai HTTP ke upstream, gunakan `proxy_pass http://127.0.0.1:18443` dan sesuaikan konfigurasi upstream. Konfigurasi default project menyediakan HTTPS internal.

## 6. Sertifikat TLS Publik

Contoh penerbitan sertifikat dengan Certbot:

```bash
sudo certbot --nginx -d absen.example.com
sudo certbot renew --dry-run
```

Jangan menggunakan sertifikat self-signed Docker sebagai sertifikat publik.

## 7. Verifikasi Go Live

```bash
curl -fsS https://absen.example.com/api/health
```

Periksa melalui browser:

- Halaman login tampil menggunakan HTTPS.
- Tidak ada kredensial demo pada halaman login.
- Login administrator berhasil.
- Dashboard, QR scanner, upload, dan check-in berfungsi.
- Port backend, frontend, dan database tidak dapat diakses melalui IP publik.

Swagger, ReDoc, dan OpenAPI dinonaktifkan ketika `APP_ENV=production`.

## Seeder Data Demo

Seeder tidak berjalan otomatis saat startup dan tidak membuat akun admin. Gunakan hanya untuk verifikasi deployment atau demo internal.

Buat dataset demo yang terisolasi:

```bash
docker compose exec backend python -m app.seed
```

Seeder aman dijalankan ulang. Jika dataset dengan nama marker yang sama sudah ada, tidak ada data baru yang dibuat.

Dataset berisi 10 peserta dengan data perusahaan, jabatan, kontak, meja, dan QR yang realistis. Dua grup delegasi juga disediakan: satu grup berisi tiga peserta dan satu grup berisi dua peserta. Sebagian peserta sudah check-in, sebagian belum, dan beberapa check-in tercatat sebagai kehadiran melalui wakil agar alur operasional dapat diuji seperti event nyata.

Hapus hanya dataset demo:

```bash
docker compose exec backend python -m app.seed --remove
```

Seeder menggunakan event `Vendor Partnership Summit 2026` dengan marker internal `[seed:vendor-partnership-2026]`. Jalankan `python -m app.seed` kembali jika ingin menyegarkan seluruh dataset seed tersebut. Jangan gunakan seeder ini untuk data event production nyata. Backup database sebelum membuat atau menghapus dataset.

## Update Versi

Backup database sebelum update:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "backup-$(date +%Y%m%d-%H%M%S).dump"
```

Update source dan rebuild:

```bash
git pull --ff-only
docker compose config --quiet
docker compose up -d --build
```

Periksa hasil update:

```bash
docker compose ps
docker compose logs --tail 100 backend
```

`docker compose up -d --build` tidak menghapus named volume database.

## Backup Dan Restore

Backup manual:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > backup.dump
```

Restore ke database maintenance:

```bash
cat backup.dump | docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
```

Simpan backup di lokasi berbeda dari server production dan uji restore secara berkala.

## Operasional

Melihat status dan log:

```bash
docker compose ps
docker compose logs --tail 100 backend
```

Restart tanpa menghapus data:

```bash
docker compose restart backend frontend proxy
```

Stop tanpa menghapus volume:

```bash
docker compose down
```

Jangan menjalankan perintah berikut pada production kecuali ingin menghapus database:

```bash
docker compose down -v
docker volume rm absen-qr-event_postgres_data
```

## Troubleshooting

- Login gagal pada deploy pertama: periksa `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`, dan log backend.
- CORS error: pastikan `CORS_ORIGINS` sama persis dengan origin HTTPS tanpa trailing slash.
- Reverse proxy 502: pastikan proxy Docker aktif dan `127.0.0.1:18443` dapat diakses dari host.
- Database gagal setelah mengganti `POSTGRES_PASSWORD`: password user PostgreSQL pada volume lama tidak berubah otomatis.
- Port bentrok: ubah `HTTPS_PORT` ke port non-default lain, lalu jalankan `docker compose up -d`.

## Checklist Go Live

- [ ] DNS domain mengarah ke server.
- [ ] `.env` berisi secret production, bukan placeholder.
- [ ] `PUBLIC_BIND_IP=127.0.0.1`.
- [ ] `HTTPS_PORT` menggunakan port non-default.
- [ ] Hanya `proxy` yang memiliki port mapping ke host.
- [ ] CORS memakai domain HTTPS production.
- [ ] Sertifikat TLS publik aktif dan renewal terjadwal.
- [ ] Login administrator berhasil.
- [ ] Backup database pertama sudah dibuat.
- [ ] Firewall hanya membuka port publik reverse proxy, biasanya `80` dan `443`.
- [ ] Port `18443`, backend, frontend, dan PostgreSQL tidak dibuka ke internet.
