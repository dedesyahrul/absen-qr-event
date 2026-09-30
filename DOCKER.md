# Docker Guide - Absen QR Event (Gatherly)

## Prasyarat

- Docker Desktop terinstal dan running
- Port 18081, 18082, 55432 tersedia

---

## Setup Awal

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build dan jalankan semua service
docker compose up -d --build
```

Tunggu hingga semua container running, lalu buka:

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:18082        |
| API      | http://localhost:18081/api    |
| API Docs | http://localhost:18081/docs   |

Login: `admin@example.com` / `admin123`

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

> **Peringatan:** flag `-v` menghapus volume `postgres_data` dan `frontend_modules`. Semua data peserta, event, dan attendance akan hilang.

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

## Akses dari HP (Jaringan LAN)

### 1. Cek IP komputer

```powershell
ipconfig
```

Cari alamat IPv4 di adapter Wi-Fi (contoh: `10.68.61.148`).

### 2. Buka firewall (PowerShell as Administrator)

```powershell
netsh advfirewall firewall add rule name="Gatherly Backend 18081" dir=in action=allow protocol=TCP localport=18081
netsh advfirewall firewall add rule name="Gatherly Frontend 18082" dir=in action=allow protocol=TCP localport=18082
```

### 3. Buka dari browser HP

```
http://<IP_KOMPUTER>:18082
```

Contoh: `http://10.68.61.148:18082`

### Hapus firewall rule (jika sudah tidak dibutuhkan)

```powershell
netsh advfirewall firewall delete rule name="Gatherly Backend 18081"
netsh advfirewall firewall delete rule name="Gatherly Frontend 18082"
```

---

## Struktur Service

```
docker compose
├── db        - PostgreSQL 16 (port 55432)
├── backend   - FastAPI + Uvicorn (port 18081)
└── frontend  - Vue 3 + Vite dev server (port 18082)
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

---

## Troubleshooting

### Container tidak mau start

```bash
# Cek log error
docker compose logs backend
docker compose logs frontend

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

### Port sudah dipakai

Edit `.env` dan ganti port yang bentrok:

```env
BACKEND_PORT=19081
FRONTEND_PORT=19082
```

Lalu rebuild:

```bash
docker compose up -d --build
```
