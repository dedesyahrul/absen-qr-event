# Migrasi Database — Gatherly v2

Panduan upgrade database dari v1 ke v2 di Docker VPS.

---

## Apa yang Berubah di v2

### Tabel Baru

| Tabel | Keterangan |
|-------|------------|
| `tables` | Data meja/kursi per event |

### Kolom Baru di Tabel `participants`

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `table_id` | FK -> tables.id, nullable | Meja peserta |
| `seat_number` | String(10), nullable | Nomor kursi |
| `check_out_at` | DateTime, nullable | Waktu checkout |
| `check_out_method` | String(20), nullable | Metode checkout |
| `check_out_by` | FK -> users.id, nullable | Siapa yang checkout |
| `created_at` | DateTime | Waktu dibuat |
| `updated_at` | DateTime | Waktu terakhir diubah |

### Kolom Baru di Tabel `users`, `events`, `vendors`

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `updated_at` | DateTime | Waktu terakhir diubah |

### Kolom Baru di Tabel `vendors`

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `created_at` | DateTime | Waktu dibuat |
| `updated_at` | DateTime | Waktu terakhir diubah |

---

## Pilih Metode Migrasi

### A. Fresh Install (Tidak Ada Data / Data Boleh Dihapus)

Cara paling mudah. Cocok untuk VPS baru atau jika data lama tidak penting.

```bash
# 1. Pull code terbaru
cd /path/to/absen-qr-event
git pull origin main

# 2. Stop dan hapus semua container + volume (DATA HILANG!)
docker compose down -v

# 3. Build ulang dan start
docker compose up -d --build

# 4. Verifikasi
docker compose ps
docker compose logs backend --tail 20
```

Sistem akan otomatis:
- Buat semua tabel baru dari nol
- Seed data demo (admin user, event, vendor, peserta, meja)

---

### B. Migrasi Manual (Pertahankan Data Lama)

Gunakan ini jika VPS sudah punya data peserta/event yang tidak boleh hilang.

#### Langkah 1: Pull Code Terbaru

```bash
cd /path/to/absen-qr-event
git pull origin main
```

#### Langkah 2: Rebuild Backend (Install openpyxl)

```bash
docker compose build backend
```

#### Langkah 3: Jalankan SQL Migrasi

Masuk ke container database:

```bash
docker compose exec db psql -U absen -d absen_qr
```

Lalu jalankan SQL berikut satu per satu:

```sql
-- 1. Buat tabel baru: tables
CREATE TABLE IF NOT EXISTS tables (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    table_number VARCHAR(20) NOT NULL,
    table_label VARCHAR(100) DEFAULT '',
    capacity INTEGER DEFAULT 8,
    zone VARCHAR(50) DEFAULT 'Regular',
    status VARCHAR(20) DEFAULT 'available'
);
CREATE INDEX IF NOT EXISTS ix_tables_event_id ON tables(event_id);

-- 2. Tambah kolom baru di participants
ALTER TABLE participants ADD COLUMN IF NOT EXISTS table_id INTEGER REFERENCES tables(id) ON DELETE SET NULL;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS seat_number VARCHAR(10);
ALTER TABLE participants ADD COLUMN IF NOT EXISTS check_out_at TIMESTAMPTZ;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS check_out_method VARCHAR(20);
ALTER TABLE participants ADD COLUMN IF NOT EXISTS check_out_by INTEGER REFERENCES users(id);
ALTER TABLE participants ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE participants ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS ix_participants_table_id ON participants(table_id);

-- 3. Tambah kolom updated_at di users
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 4. Tambah kolom updated_at di events
ALTER TABLE events ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 5. Tambah kolom created_at dan updated_at di vendors
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 6. Verifikasi
\dt
\d participants
\d tables
```

Keluar dari psql:

```
\q
```

#### Langkah 4: Restart Backend

```bash
docker compose restart backend
```

#### Langkah 5: Restart Frontend + Nginx

```bash
docker compose restart frontend nginx
```

#### Langkah 6: Verifikasi

```bash
# Cek semua container running
docker compose ps

# Cek backend tidak ada error
docker compose logs backend --tail 20

# Test API
curl -s http://localhost:18081/api/health
# Harus return: {"status":"ok","database":true}

# Test endpoint baru (tables)
# Login dulu, lalu:
curl -s -H "Authorization: Bearer TOKEN" http://localhost:18081/api/events/1/tables
# Harus return: [] (kosong, belum ada meja)
```

---

## Metode C: Script Otomatis (Copy-Paste)

Satu script yang menjalankan semua langkah migrasi manual:

```bash
#!/bin/bash
# migrate-v2.sh — Jalankan di server VPS

set -e
cd /path/to/absen-qr-event

echo "=== Pull code terbaru ==="
git pull origin main

echo "=== Rebuild backend ==="
docker compose build backend

echo "=== Jalankan migrasi database ==="
docker compose exec -T db psql -U absen -d absen_qr <<'SQL'
CREATE TABLE IF NOT EXISTS tables (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    table_number VARCHAR(20) NOT NULL,
    table_label VARCHAR(100) DEFAULT '',
    capacity INTEGER DEFAULT 8,
    zone VARCHAR(50) DEFAULT 'Regular',
    status VARCHAR(20) DEFAULT 'available'
);
CREATE INDEX IF NOT EXISTS ix_tables_event_id ON tables(event_id);

ALTER TABLE participants ADD COLUMN IF NOT EXISTS table_id INTEGER REFERENCES tables(id) ON DELETE SET NULL;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS seat_number VARCHAR(10);
ALTER TABLE participants ADD COLUMN IF NOT EXISTS check_out_at TIMESTAMPTZ;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS check_out_method VARCHAR(20);
ALTER TABLE participants ADD COLUMN IF NOT EXISTS check_out_by INTEGER REFERENCES users(id);
ALTER TABLE participants ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE participants ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS ix_participants_table_id ON participants(table_id);

ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE events ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
SQL

echo "=== Restart semua service ==="
docker compose restart backend frontend nginx

echo "=== Verifikasi ==="
sleep 5
docker compose ps
echo ""
echo "=== Health check ==="
curl -s http://localhost:18081/api/health
echo ""
echo ""
echo "Migrasi selesai!"
```

Simpan sebagai `migrate-v2.sh`, lalu jalankan:

```bash
chmod +x migrate-v2.sh
./migrate-v2.sh
```

---

## Backup Sebelum Migrasi

Sangat disarankan untuk backup database sebelum migrasi:

### Backup

```bash
# Export seluruh database ke file SQL
docker compose exec db pg_dump -U absen absen_qr > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore (jika perlu rollback)

```bash
# Restore dari backup
cat backup_20261001_120000.sql | docker compose exec -T db psql -U absen -d absen_qr
```

---

## Troubleshooting

### Error: relation "tables" already exists

Tidak masalah. Perintah `CREATE TABLE IF NOT EXISTS` akan di-skip jika tabel sudah ada.

### Error: column "table_id" of relation "participants" already exists

Tidak masalah. Perintah `ADD COLUMN IF NOT EXISTS` akan di-skip jika kolom sudah ada.

### Backend error setelah migrasi

```bash
# Cek log error
docker compose logs backend --tail 50

# Jika ada error model/kolom, pastikan semua SQL di atas sudah dijalankan
# Lalu restart backend
docker compose restart backend
```

### Data lama tidak tampil di frontend

Peserta lama akan memiliki `table_id = NULL` dan `seat_number = NULL`. Ini normal — mereka belum di-assign meja. Bisa di-assign lewat UI atau import Excel.

### Ingin reset total (mulai dari nol)

```bash
docker compose down -v
docker compose up -d --build
```

---

## Catatan

- Script migrasi ini **idempotent** — aman dijalankan berkali-kali. `IF NOT EXISTS` memastikan tidak ada duplikasi.
- Migrasi ini hanya menambah tabel/kolom baru. Tidak ada data yang dihapus atau diubah.
- Setelah migrasi, semua peserta lama tetap berfungsi normal dengan `table_id = NULL`.
- QR token peserta lama **tidak berubah** — QR code yang sudah dicetak tetap valid.
