# Konsep Upgrade: Gatherly v2 — Event Registration & Check-in System

> Dokumen ini adalah blueprint lengkap untuk upgrade sistem Gatherly dari sistem absensi QR sederhana menjadi **Event Registration & Check-in System** yang lengkap dan production-ready.

---

## Daftar Isi

1. [Ringkasan Upgrade](#1-ringkasan-upgrade)
2. [Fitur Baru: Seating Management](#2-fitur-baru-seating-management)
3. [Fitur Baru: Import & Export Excel](#3-fitur-baru-import--export-excel)
4. [Fitur Baru: Manajemen Multi-Event](#4-fitur-baru-manajemen-multi-event)
5. [Fitur Baru: User & Staff Management](#5-fitur-baru-user--staff-management)
6. [Fitur Baru: CRUD Lengkap](#6-fitur-baru-crud-lengkap)
7. [Fitur Baru: Attendance Report & Analytics](#7-fitur-baru-attendance-report--analytics)
8. [Fitur Baru: Live Dashboard (Real-time)](#8-fitur-baru-live-dashboard-real-time)
9. [Fitur Baru: Guest Badge / Name Tag Generator](#9-fitur-baru-guest-badge--name-tag-generator)
10. [Fitur Baru: Undo Check-in & Check-out](#10-fitur-baru-undo-check-in--check-out)
11. [Fitur Baru: Notifikasi & Sound Effect](#11-fitur-baru-notifikasi--sound-effect)
12. [Perubahan Database Schema](#12-perubahan-database-schema)
13. [Perubahan API Endpoints](#13-perubahan-api-endpoints)
14. [Prioritas Implementasi](#14-prioritas-implementasi)

---

## 1. Ringkasan Upgrade

### Kondisi Saat Ini (v1)

| Aspek | Status |
|-------|--------|
| Tambah peserta | Satu per satu via form |
| Edit/Hapus data | Tidak bisa |
| Nomor kursi/meja | Tidak ada |
| Import dari Excel | Tidak ada |
| Export ke Excel | Tidak ada |
| Multi-event | Frontend hanya load event pertama |
| User management | Hanya 1 admin dari seed data |
| Laporan/Report | Tidak ada |
| Real-time update | Manual refresh |
| Undo check-in | Tidak bisa |

### Target Upgrade (v2)

| Aspek | Target |
|-------|--------|
| Tambah peserta | Form + bulk import dari Excel |
| Edit/Hapus data | CRUD lengkap untuk semua entitas |
| Nomor kursi/meja | Assign meja & kursi per peserta |
| Import dari Excel | Upload file .xlsx/.csv → auto-create peserta + vendor |
| Export ke Excel | Download data peserta, attendance, laporan |
| Multi-event | Dropdown pilih event, buat event baru |
| User management | Tambah/kelola staff & operator |
| Laporan/Report | Summary, per-vendor, per-waktu, export PDF/Excel |
| Real-time update | WebSocket push untuk dashboard |
| Undo check-in | Bisa batalkan check-in |

---

## 2. Fitur Baru: Seating Management

### Konsep

Setiap peserta bisa di-assign ke **nomor meja** dan **nomor kursi**. Saat check-in, petugas bisa langsung memberitahu peserta posisi duduknya.

### Database Schema Baru

#### Tabel `tables` (meja)

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | Integer, PK | Auto-increment |
| event_id | FK → events.id | Event yang memiliki meja ini |
| table_number | String(20) | Nomor/nama meja (misal: "A1", "VIP-1", "Meja 12") |
| table_label | String(100) | Label/deskripsi (misal: "Meja Utama", "Dekat Panggung") |
| capacity | Integer | Kapasitas kursi di meja ini |
| zone | String(50) | Zona/area (misal: "VIP", "Regular", "Balcony") |
| status | String(20) | "available", "full", "reserved" |

#### Perubahan Tabel `participants`

| Kolom Baru | Tipe | Keterangan |
|------------|------|------------|
| table_id | FK → tables.id, nullable | Meja yang ditempati |
| seat_number | String(10), nullable | Nomor kursi di meja tersebut (misal: "1", "2", "A") |

### Alur Penggunaan

```
1. Admin buat daftar meja untuk event
   └── Meja A1 (kapasitas 8, zona VIP)
   └── Meja A2 (kapasitas 8, zona VIP)
   └── Meja B1 (kapasitas 10, zona Regular)
   └── ...

2. Assign peserta ke meja + kursi
   └── Bisa saat import Excel (kolom meja & kursi)
   └── Bisa manual via form edit peserta
   └── Bisa drag-and-drop di seating map (future)

3. Saat check-in (scan QR)
   └── Tampilkan info: "Selamat datang, Nadia! Meja A1, Kursi 3"
   └── Petugas langsung arahkan peserta
```

### UI: Seating View (Frontend Baru)

- **Tab baru di sidebar**: "Seating"
- **Tampilan tabel/grid**: Semua meja dengan status occupancy
- **Klik meja** → lihat siapa saja yang duduk di meja itu
- **Assign peserta** → dropdown atau drag dari daftar peserta yang belum di-assign
- **Filter**: berdasarkan zona, status (kosong/penuh), vendor
- **Info di scan result**: Setelah scan QR, tampilkan meja + kursi peserta

### API Endpoints Baru

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/events/{id}/tables` | List semua meja di event |
| POST | `/api/events/{id}/tables` | Buat meja baru |
| PUT | `/api/events/{id}/tables/{table_id}` | Update meja |
| DELETE | `/api/events/{id}/tables/{table_id}` | Hapus meja |
| POST | `/api/events/{id}/tables/bulk` | Buat banyak meja sekaligus (misal: "A1-A10") |
| PATCH | `/api/events/{id}/participants/{pid}/seat` | Assign peserta ke meja + kursi |

---

## 3. Fitur Baru: Import & Export Excel

### 3.1 Import Peserta dari Excel

#### Format Template Excel

| Kolom | Wajib | Contoh | Keterangan |
|-------|-------|--------|------------|
| nama | Ya | Nadia Prameswari | Nama lengkap peserta |
| perusahaan | Ya | PT Karya Nusantara | Nama vendor/perusahaan |
| jabatan | Tidak | Manager | Posisi/jabatan |
| telepon | Tidak | 08123456789 | Nomor telepon |
| email | Tidak | nadia@karya.com | Email peserta |
| kategori_perusahaan | Tidak | Strategic Partner | Kategori vendor |
| nomor_meja | Tidak | A1 | Nomor meja (auto-create jika belum ada) |
| nomor_kursi | Tidak | 3 | Nomor kursi di meja |

#### Alur Import

```
1. Admin download template Excel (kosong, dengan header yang benar)
2. Admin isi data peserta di Excel
3. Upload file .xlsx atau .csv ke sistem
4. Sistem preview data:
   ├── Tampilkan jumlah baris yang terbaca
   ├── Validasi: baris yang error (nama kosong, duplikat, dll)
   ├── Auto-detect vendor baru vs yang sudah ada
   └── Auto-detect meja baru vs yang sudah ada
5. Admin konfirmasi import
6. Sistem:
   ├── Buat vendor baru jika belum ada
   ├── Buat meja baru jika belum ada
   ├── Buat peserta + generate QR token
   └── Return laporan: X berhasil, Y gagal, Z vendor baru dibuat
```

#### Handling Duplikat

- Cek duplikat berdasarkan **nama + perusahaan** (case-insensitive)
- Opsi saat duplikat ditemukan:
  - **Skip** — lewati baris duplikat
  - **Update** — update data yang sudah ada dengan data baru
  - **Buat baru** — tetap buat entri baru (mungkin orang beda dengan nama sama)

#### API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/events/{id}/import/template` | Download template Excel kosong |
| POST | `/api/events/{id}/import/preview` | Upload file → return preview + validasi |
| POST | `/api/events/{id}/import/confirm` | Konfirmasi import setelah preview |

### 3.2 Export Data ke Excel

#### Jenis Export

| Export | Isi File | Nama File |
|--------|----------|-----------|
| **Daftar Peserta** | Semua peserta dengan info vendor, meja, kursi, status | `peserta_{event}_{tanggal}.xlsx` |
| **Laporan Kehadiran** | Peserta + waktu check-in + metode + siapa yang scan | `kehadiran_{event}_{tanggal}.xlsx` |
| **Daftar Vendor** | Semua vendor dengan jumlah peserta dan rate kehadiran | `vendor_{event}_{tanggal}.xlsx` |
| **Layout Meja** | Semua meja dengan daftar peserta per meja | `seating_{event}_{tanggal}.xlsx` |
| **Audit Log** | Semua log scan (termasuk yang gagal) | `audit_{event}_{tanggal}.xlsx` |

#### Format Output Excel

Setiap file Excel memiliki:
- **Header row** dengan style bold + background color
- **Auto-fit column width**
- **Sheet name** sesuai konten
- **Footer**: tanggal export, nama event, total record

#### API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/events/{id}/export/participants` | Export daftar peserta |
| GET | `/api/events/{id}/export/attendance` | Export laporan kehadiran |
| GET | `/api/events/{id}/export/vendors` | Export daftar vendor |
| GET | `/api/events/{id}/export/seating` | Export layout meja |
| GET | `/api/events/{id}/export/audit-log` | Export audit log |

### 3.3 Library yang Dibutuhkan

**Backend (Python):**
- `openpyxl` — Baca/tulis file Excel (.xlsx)

**Frontend:**
- Tidak perlu library tambahan (download langsung dari API sebagai file)

---

## 4. Fitur Baru: Manajemen Multi-Event

### Kondisi Saat Ini

Frontend selalu load `events[0]` — tidak bisa pilih atau buat event lain.

### Upgrade

- **Event selector** di sidebar — dropdown pilih event aktif
- **Buat event baru** — form modal di frontend
- **Event status management**: `draft` → `active` → `completed` → `archived`
- **Copy event** — duplicate event beserta vendor dan meja (tanpa peserta)
- **Arsip event** — event lama bisa diarsip, tidak tampil di dropdown tapi datanya tetap ada

### UI Changes

- Sidebar: dropdown event selector menggantikan info event statis
- Halaman "Events" baru (opsional): list card semua event dengan statistik

---

## 5. Fitur Baru: User & Staff Management

### Role System

| Role | Hak Akses |
|------|-----------|
| **admin** | Semua fitur, kelola user, kelola event, import/export, hapus data |
| **operator** | Scan QR, manual check-in, lihat dashboard & peserta, tidak bisa hapus |
| **viewer** | Hanya lihat dashboard dan data, tidak bisa scan atau edit |

### API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/users` | List semua user (admin only) |
| POST | `/api/users` | Buat user baru (admin only) |
| PUT | `/api/users/{id}` | Update user (admin only) |
| DELETE | `/api/users/{id}` | Nonaktifkan user (admin only) |
| PUT | `/api/auth/password` | Ganti password sendiri |

### UI

- **Halaman "Settings"** atau **"Staff"** di sidebar (admin only)
- Form tambah user dengan role selection
- Tabel user aktif dengan toggle aktif/nonaktif

---

## 6. Fitur Baru: CRUD Lengkap

### Endpoints yang Perlu Ditambahkan

#### Events

| Method | Path | Keterangan |
|--------|------|------------|
| PUT | `/api/events/{id}` | Update event |
| DELETE | `/api/events/{id}` | Hapus/arsipkan event |

#### Vendors

| Method | Path | Keterangan |
|--------|------|------------|
| PUT | `/api/events/{id}/vendors/{vid}` | Update vendor |
| DELETE | `/api/events/{id}/vendors/{vid}` | Hapus vendor |

#### Participants

| Method | Path | Keterangan |
|--------|------|------------|
| PUT | `/api/events/{id}/participants/{pid}` | Update peserta |
| DELETE | `/api/events/{id}/participants/{pid}` | Hapus peserta |
| DELETE | `/api/events/{id}/participants` | Bulk delete peserta (dengan body berisi list ID) |

### UI Changes

- **Tombol edit** (ikon pensil) di setiap row tabel peserta dan vendor
- **Tombol hapus** (ikon trash) dengan konfirmasi dialog
- **Inline edit** untuk field sederhana (nama, telepon)
- **Modal edit** untuk perubahan besar (ganti vendor, ganti meja)

---

## 7. Fitur Baru: Attendance Report & Analytics

### Dashboard Analytics Upgrade

#### Statistik Tambahan

- **Check-in per jam** — bar chart menunjukkan distribusi waktu kedatangan
- **Rate per vendor** — ranking vendor berdasarkan attendance rate
- **Metode check-in** — pie chart QR vs manual
- **Occupancy meja** — persentase meja yang sudah terisi

#### Laporan yang Bisa Dihasilkan

| Laporan | Konten |
|---------|--------|
| **Summary Report** | Total undangan, hadir, tidak hadir, rate, breakdown per vendor |
| **Timeline Report** | Check-in per interval waktu (per 15 menit / per jam) |
| **No-show Report** | Daftar peserta yang tidak hadir |
| **Seating Report** | Status meja, kursi kosong, peserta belum di-assign meja |

### API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/events/{id}/reports/summary` | Data summary keseluruhan |
| GET | `/api/events/{id}/reports/timeline` | Data check-in per interval waktu |
| GET | `/api/events/{id}/reports/no-show` | Daftar yang tidak hadir |
| GET | `/api/events/{id}/attendance-logs` | Query attendance logs dengan filter |

---

## 8. Fitur Baru: Live Dashboard (Real-time)

### Konsep

Saat ini dashboard harus di-refresh manual. Upgrade ke **real-time push** menggunakan Server-Sent Events (SSE) — lebih sederhana dari WebSocket dan cukup untuk use case ini.

### Implementasi

```
Backend:
  - Endpoint SSE: GET /api/events/{id}/live
  - Setiap kali ada check-in, push event ke semua client yang listening
  - Data yang di-push: summary terbaru + info peserta yang baru check-in

Frontend:
  - EventSource connection ke /api/events/{id}/live
  - Auto-update dashboard stats tanpa reload
  - Animasi "pop" saat ada peserta baru check-in
  - Sound notification (opsional, bisa on/off)
```

### Keuntungan

- Bisa buka dashboard di layar besar (TV/projector) di venue — auto-update
- Operator scan di HP, dashboard di TV langsung berubah

---

## 9. Fitur Baru: Guest Badge / Name Tag Generator

### Konsep

Generate template name tag / badge yang siap cetak untuk setiap peserta, berisi:

```
┌─────────────────────────┐
│      GATHERLY 2026      │
│   Vendor Gathering      │
├─────────────────────────┤
│                         │
│   Nadia Prameswari      │
│   PT Karya Nusantara    │
│   Manager               │
│                         │
│   ┌─────┐  Meja: A1    │
│   │ QR  │  Kursi: 3    │
│   │CODE │               │
│   └─────┘               │
│                         │
│   #001                  │
└─────────────────────────┘
```

### Fitur

- **Generate badge per peserta** — download sebagai PNG/PDF
- **Bulk generate** — semua peserta dalam satu PDF (layout A4, 4-6 badge per halaman)
- **Template customizable** — nama event, logo, warna bisa disesuaikan
- **Include QR code** — QR kode tertanam di badge, peserta tinggal tunjukkan badge untuk scan

### API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/events/{id}/participants/{pid}/badge` | Generate badge satu peserta (PNG) |
| GET | `/api/events/{id}/badges` | Generate semua badge dalam satu PDF |

---

## 10. Fitur Baru: Undo Check-in & Check-out

### Konsep

- **Undo check-in** — batalkan check-in jika salah scan (admin/operator)
- **Check-out** — catat waktu keluar peserta (opsional, untuk tracking durasi kehadiran)

### Perubahan Database

Tambah kolom di tabel `participants`:

| Kolom Baru | Tipe | Keterangan |
|------------|------|------------|
| check_out_at | DateTime(tz), nullable | Waktu keluar |
| check_out_method | String(20), nullable | "qr", "manual" |
| check_out_by | FK → users.id, nullable | Siapa yang checkout |

### API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| POST | `/api/events/{id}/attendance/undo` | Batalkan check-in (reset status ke not_attended) |
| POST | `/api/events/{id}/attendance/checkout` | Catat check-out peserta |

---

## 11. Fitur Baru: Notifikasi & Sound Effect

### Sound Effects

- **Scan berhasil** → bunyi "ding" sukses
- **Scan gagal / sudah check-in** → bunyi warning
- **QR tidak valid** → bunyi error

### Visual Notification

- **Toast notification** di pojok kanan atas untuk setiap check-in
- **Animasi confetti** saat milestone tercapai (50%, 75%, 100% kehadiran)
- **Counter live** di topbar menunjukkan jumlah check-in hari ini

---

## 12. Perubahan Database Schema

### Schema Lengkap (v2)

```
users
  ├── id (PK)
  ├── name
  ├── email (UNIQUE)
  ├── password_hash
  ├── role (admin/operator/viewer)
  ├── is_active
  ├── created_at
  └── updated_at                    ← BARU

events
  ├── id (PK)
  ├── name
  ├── description
  ├── event_date
  ├── start_time
  ├── end_time
  ├── location
  ├── status (draft/active/completed/archived)
  ├── created_at
  └── updated_at                    ← BARU

vendors
  ├── id (PK)
  ├── event_id (FK → events)
  ├── company_name
  ├── category
  ├── contact_name
  ├── phone
  ├── email
  ├── created_at                    ← BARU
  └── updated_at                    ← BARU

tables                              ← TABEL BARU
  ├── id (PK)
  ├── event_id (FK → events)
  ├── table_number
  ├── table_label
  ├── capacity
  ├── zone
  └── status

participants
  ├── id (PK)
  ├── event_id (FK → events)
  ├── vendor_id (FK → vendors, nullable)
  ├── table_id (FK → tables, nullable)  ← BARU
  ├── seat_number                        ← BARU
  ├── name
  ├── position
  ├── phone
  ├── email
  ├── qr_token (UNIQUE)
  ├── attendance_status
  ├── check_in_at
  ├── check_in_method
  ├── checked_in_by (FK → users)
  ├── check_out_at                       ← BARU
  ├── check_out_method                   ← BARU
  ├── check_out_by (FK → users)          ← BARU
  ├── created_at                         ← BARU
  └── updated_at                         ← BARU

attendance_logs (tidak berubah)
  ├── id (PK)
  ├── event_id (FK → events)
  ├── participant_id (FK → participants)
  ├── action
  ├── method
  ├── result
  ├── scanned_by (FK → users)
  ├── scanned_at
  └── notes
```

---

## 13. Perubahan API Endpoints

### Rangkuman Semua Endpoint (v2)

#### System
| Method | Path | Status |
|--------|------|--------|
| GET | `/api` | Ada |
| GET | `/api/health` | Ada |

#### Auth
| Method | Path | Status |
|--------|------|--------|
| POST | `/api/auth/login` | Ada |
| GET | `/api/auth/me` | Ada |
| PUT | `/api/auth/password` | **BARU** |

#### Users (admin only)
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/users` | **BARU** |
| POST | `/api/users` | **BARU** |
| PUT | `/api/users/{id}` | **BARU** |
| DELETE | `/api/users/{id}` | **BARU** |

#### Events
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events` | Ada |
| POST | `/api/events` | Ada |
| GET | `/api/events/{id}` | Ada |
| PUT | `/api/events/{id}` | **BARU** |
| DELETE | `/api/events/{id}` | **BARU** |
| GET | `/api/events/{id}/dashboard` | Ada |

#### Vendors
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/vendors` | Ada |
| POST | `/api/events/{id}/vendors` | Ada |
| PUT | `/api/events/{id}/vendors/{vid}` | **BARU** |
| DELETE | `/api/events/{id}/vendors/{vid}` | **BARU** |

#### Tables (Seating)
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/tables` | **BARU** |
| POST | `/api/events/{id}/tables` | **BARU** |
| PUT | `/api/events/{id}/tables/{tid}` | **BARU** |
| DELETE | `/api/events/{id}/tables/{tid}` | **BARU** |
| POST | `/api/events/{id}/tables/bulk` | **BARU** |

#### Participants
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/participants` | Ada |
| POST | `/api/events/{id}/participants` | Ada |
| PUT | `/api/events/{id}/participants/{pid}` | **BARU** |
| DELETE | `/api/events/{id}/participants/{pid}` | **BARU** |
| PATCH | `/api/events/{id}/participants/{pid}/seat` | **BARU** |

#### Attendance
| Method | Path | Status |
|--------|------|--------|
| POST | `/api/events/{id}/attendance/scan` | Ada |
| POST | `/api/events/{id}/attendance/manual` | Ada |
| POST | `/api/events/{id}/attendance/undo` | **BARU** |
| POST | `/api/events/{id}/attendance/checkout` | **BARU** |

#### QR Code
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/participants/{pid}/qr` | Ada |
| GET | `/api/events/{id}/participants/qr-all` | Ada |

#### Import & Export
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/import/template` | **BARU** |
| POST | `/api/events/{id}/import/preview` | **BARU** |
| POST | `/api/events/{id}/import/confirm` | **BARU** |
| GET | `/api/events/{id}/export/participants` | **BARU** |
| GET | `/api/events/{id}/export/attendance` | **BARU** |
| GET | `/api/events/{id}/export/vendors` | **BARU** |
| GET | `/api/events/{id}/export/seating` | **BARU** |
| GET | `/api/events/{id}/export/audit-log` | **BARU** |

#### Reports
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/reports/summary` | **BARU** |
| GET | `/api/events/{id}/reports/timeline` | **BARU** |
| GET | `/api/events/{id}/reports/no-show` | **BARU** |
| GET | `/api/events/{id}/attendance-logs` | **BARU** |

#### Badge
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/participants/{pid}/badge` | **BARU** |
| GET | `/api/events/{id}/badges` | **BARU** |

#### Live (SSE)
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/events/{id}/live` | **BARU** |

**Total:** 16 endpoint yang sudah ada + **29 endpoint baru** = **45 endpoint**

---

## 14. Prioritas Implementasi

### Fase 1 — Fondasi (Harus Duluan)

| No | Fitur | Alasan |
|----|-------|--------|
| 1 | CRUD lengkap (update/delete) semua entitas | Dasar yang wajib ada sebelum fitur lain |
| 2 | Import peserta dari Excel | Kebutuhan utama, input data manual sangat lambat |
| 3 | Export data ke Excel | Kebutuhan utama, pelaporan |
| 4 | Seating management (meja & kursi) | Fitur yang diminta langsung |

### Fase 2 — Operational Excellence

| No | Fitur | Alasan |
|----|-------|--------|
| 5 | Undo check-in | Penting untuk koreksi kesalahan |
| 6 | Multi-event management | Supaya bisa pakai untuk banyak event |
| 7 | Attendance logs query | Audit trail harus bisa dibaca |
| 8 | Report & analytics | Nilai tambah besar untuk panitia |

### Fase 3 — Advanced Features

| No | Fitur | Alasan |
|----|-------|--------|
| 9 | User & staff management | Role-based access |
| 10 | Live dashboard (SSE) | Tampilan real-time di venue |
| 11 | Sound effects & notifikasi | UX improvement |
| 12 | Badge / name tag generator | Nice-to-have, hemat waktu cetak |
| 13 | Check-out tracking | Opsional, tergantung kebutuhan event |

### Dependency Python Baru

```
openpyxl==3.1.5          # Baca/tulis Excel (.xlsx)
sse-starlette==2.1.0     # Server-Sent Events untuk FastAPI
reportlab==4.2.5         # Generate PDF (badge/report) — opsional fase 3
```

---

> **Dokumen ini adalah panduan konsep. Implementasi akan dilakukan per fase sesuai prioritas di atas.**
