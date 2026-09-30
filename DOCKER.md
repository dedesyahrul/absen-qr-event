# Docker Guide - Absen QR Event (Gatherly)

## Prasyarat

- Docker & Docker Compose terinstal dan running
- Port 80, 443, 18081, 18082, 55432 tersedia

---

## Setup Awal

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build dan jalankan semua service
docker compose up -d --build
```

Tunggu hingga semua container running, lalu buka:

| Akses       | URL                                  | Keterangan                      |
|-------------|--------------------------------------|---------------------------------|
| HTTPS (HP)  | https://IP_VPS                       | Untuk scan QR via kamera HP     |
| Frontend    | http://localhost:18082               | Dev langsung tanpa Nginx        |
| API         | http://localhost:18081/api           | Dev langsung tanpa Nginx        |
| API Docs    | https://IP_VPS/docs                  | Swagger via Nginx               |

Login: `admin@example.com` / `admin123`

> **Penting:** Akses dari HP harus via **HTTPS** agar kamera bisa digunakan.
> Browser akan tampilkan warning "Not Secure" karena self-signed certificate.
> Klik **Advanced** > **Proceed** untuk melanjutkan.

---

## Perintah Harian

### Start (tanpa rebuild)

```bash
docker compose up -d
```

### Stop (container tetap ada)

```bash
docker compose stop
```

### Restart semua service

```bash
docker compose restart
```

### Restart satu service saja

```bash
docker compose restart backend
docker compose restart frontend
docker compose restart nginx
docker compose restart db
```

### Lihat status container

```bash
docker compose ps
```

### Lihat log

```bash
# Semua service
docker compose logs -f

# Satu service saja
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
docker compose logs -f db

# 50 baris terakhir
docker compose logs --tail 50 backend
```

---

## Build & Rebuild

### Build pertama kali

```bash
docker compose up -d --build
```

### Rebuild setelah ubah requirements.txt atau package.json

```bash
docker compose up -d --build
```

### Rebuild satu service saja

```bash
# Contoh: hanya rebuild backend
docker compose build backend
docker compose up -d backend

# Contoh: hanya rebuild frontend
docker compose build frontend
docker compose up -d frontend
```

### Rebuild total (tanpa cache)

Gunakan ini jika ada masalah dependency atau image corrupt:

```bash
docker compose build --no-cache
docker compose up -d
```

### Rebuild total satu baris

```bash
docker compose down && docker compose up -d --build
```

---

## Clean / Reset

### Stop dan hapus container (data database tetap aman)

```bash
docker compose down
```

### Stop, hapus container + hapus database (reset total)

```bash
docker compose down -v
```

> **Peringatan:** flag `-v` menghapus volume `postgres_data`, `frontend_modules`, dan `nginx_certs`. Semua data peserta, event, attendance, dan SSL certificate akan hilang (certificate akan di-generate ulang saat start).

### Rebuild dari nol (fresh start)

```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Hapus image yang sudah tidak dipakai

```bash
docker image prune -f
```

### Hapus semua (container + volume + image project ini)

```bash
docker compose down -v --rmi all
```

### Nuclear clean (hapus semua Docker yang tidak terpakai di sistem)

```bash
docker system prune -a --volumes
```

> **Peringatan:** Ini menghapus SEMUA container, image, dan volume yang tidak sedang digunakan di seluruh Docker, bukan hanya project ini.

---

## Akses dari HP / Device Lain

### Via VPS (production)

Cukup buka dari browser HP:

```
https://IP_VPS
```

- SSL certificate otomatis di-generate saat pertama kali start
- Browser akan tampilkan warning karena self-signed cert -> klik **Advanced** > **Proceed**
- Setelah accept, kamera dan semua fitur akan berfungsi normal

### Via jaringan lokal (development)

#### 1. Cek IP komputer

```bash
# Linux/Mac
ip addr show | grep inet

# Windows
ipconfig
```

#### 2. Buka firewall (Windows - PowerShell as Administrator)

```powershell
netsh advfirewall firewall add rule name="Gatherly HTTPS 443" dir=in action=allow protocol=TCP localport=443
netsh advfirewall firewall add rule name="Gatherly HTTP 80" dir=in action=allow protocol=TCP localport=80
```

#### 3. Buka dari browser HP

```
https://<IP_KOMPUTER>
```

#### Hapus firewall rule (jika sudah tidak dibutuhkan)

```powershell
netsh advfirewall firewall delete rule name="Gatherly HTTPS 443"
netsh advfirewall firewall delete rule name="Gatherly HTTP 80"
```

---

## Struktur Service

```
docker compose
├── db        - PostgreSQL 16 (port 55432)
├── backend   - FastAPI + Uvicorn (port 18081)
├── frontend  - Vue 3 + Vite dev server (port 18082)
└── nginx     - Reverse proxy + SSL (port 80/443)
```

```
Browser (HP)
    │
    ▼ HTTPS :443
  Nginx (SSL termination)
    ├──── /        → frontend:5173
    ├──── /api     → backend:8000
    └──── /docs    → backend:8000
```

### Environment Variables (.env)

| Variable          | Default             | Keterangan            |
|-------------------|---------------------|-----------------------|
| POSTGRES_DB       | absen_qr            | Nama database         |
| POSTGRES_USER     | absen               | User database         |
| POSTGRES_PASSWORD | absen_dev_password  | Password database     |
| POSTGRES_PORT     | 55432               | Port PostgreSQL       |
| BACKEND_PORT      | 18081               | Port API backend      |
| FRONTEND_PORT     | 18082               | Port frontend         |
| HTTPS_PORT        | 443                 | Port HTTPS (Nginx)    |
| HTTP_PORT         | 80                  | Port HTTP (redirect)  |

---

## SSL Certificate

### Self-signed (default)

Certificate otomatis di-generate saat container `nginx` pertama kali start. Tersimpan di volume `nginx_certs` dan berlaku 10 tahun.

### Regenerate certificate

```bash
# Hapus volume cert lama
docker compose down
docker volume rm absen-qr-event_nginx_certs

# Start ulang (cert baru akan di-generate)
docker compose up -d
```

### Ganti ke Let's Encrypt (jika punya domain)

Jika nantinya sudah punya domain, ganti isi `nginx/default.conf` dan gunakan certbot untuk generate SSL certificate yang trusted.

---

## Troubleshooting

### Container tidak mau start

```bash
# Cek log error
docker compose logs backend
docker compose logs frontend
docker compose logs nginx

# Rebuild clean
docker compose down -v
docker compose up -d --build
```

### Database connection refused

```bash
# Pastikan db sudah healthy
docker compose ps

# Jika db belum healthy, restart
docker compose restart db
# Tunggu 10 detik lalu restart backend
docker compose restart backend
```

### Frontend blank / error

```bash
# Hapus node_modules volume dan rebuild
docker compose down
docker volume rm absen-qr-event_frontend_modules
docker compose up -d --build
```

### Kamera tidak bisa diakses dari HP

1. Pastikan akses via **HTTPS** (`https://`), bukan HTTP
2. Accept self-signed certificate warning di browser
3. Izinkan akses kamera saat browser meminta permission

### Port sudah dipakai

Edit `.env` dan ganti port yang bentrok:

```env
HTTPS_PORT=8443
HTTP_PORT=8080
BACKEND_PORT=19081
FRONTEND_PORT=19082
```

Lalu rebuild:

```bash
docker compose up -d --build
```

### Nginx 502 Bad Gateway

```bash
# Pastikan backend dan frontend sudah running
docker compose ps

# Restart nginx
docker compose restart nginx
```
