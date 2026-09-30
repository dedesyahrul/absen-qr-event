# Konsep Sistem Absensi QR Vendor Gathering

## 1. Gambaran Umum

Sistem Absensi QR Vendor Gathering adalah aplikasi berbasis web untuk mencatat kehadiran vendor atau peserta acara menggunakan QR Code unik.

Sistem ini dirancang agar proses registrasi di lokasi acara lebih cepat, mengurangi pencatatan manual, dan menyediakan data kehadiran yang dapat dipantau secara real-time oleh admin dan panitia.

## 2. Tujuan Sistem

- Mempercepat proses registrasi peserta.
- Mengurangi kesalahan pencatatan kehadiran.
- Menyediakan identitas digital untuk setiap peserta.
- Memudahkan panitia melakukan validasi peserta.
- Menyediakan dashboard kehadiran secara real-time.
- Menghasilkan laporan kehadiran yang dapat diekspor.
- Menyimpan riwayat aktivitas absensi untuk kebutuhan audit.

## 3. Ruang Lingkup

### Dalam Lingkup MVP

- Manajemen event.
- Manajemen data vendor dan peserta.
- Import data peserta dari Excel atau CSV.
- Pembuatan QR Code personal.
- Pengiriman atau distribusi QR Code kepada peserta.
- Scan QR Code menggunakan kamera perangkat.
- Check-in satu kali untuk setiap peserta.
- Pencarian peserta secara manual.
- Dashboard statistik kehadiran.
- Export laporan kehadiran.
- Pencatatan log aktivitas scan.

### Pengembangan Lanjutan

- Check-out peserta.
- RSVP sebelum acara.
- Cetak name tag otomatis.
- Check-in tamu VIP.
- Doorprize berdasarkan peserta yang hadir.
- Survey kepuasan acara.
- Integrasi WhatsApp atau email.
- Pembagian meja atau kelompok vendor.
- Broadcast kepada peserta yang belum hadir.

## 4. Aktor dan Hak Akses

### Admin

Admin memiliki akses penuh untuk:

- Membuat dan mengelola event.
- Mengelola data vendor dan peserta.
- Mengimpor data peserta.
- Membuat, mengirim ulang, atau membatalkan QR Code.
- Mengelola akun panitia.
- Melihat dashboard dan laporan.
- Mengekspor data kehadiran.
- Melihat audit log.

### Panitia Registrasi

Panitia memiliki akses untuk:

- Membuka halaman scan QR Code.
- Memindai QR Code peserta.
- Mencari peserta secara manual.
- Melakukan check-in manual setelah verifikasi identitas.
- Melihat status kehadiran peserta.

### Peserta atau Vendor

Peserta dapat:

- Menerima QR Code personal.
- Melihat informasi event.
- Menunjukkan QR Code saat registrasi.
- Melakukan konfirmasi data jika diperlukan.

## 5. Alur Bisnis

### 5.1 Persiapan Event

1. Admin login ke sistem.
2. Admin membuat event baru.
3. Admin mengisi nama, tanggal, waktu, lokasi, dan informasi event.
4. Admin memasukkan data vendor.
5. Admin menambahkan peserta dari masing-masing vendor.
6. Sistem menghasilkan QR Code unik untuk setiap peserta.
7. QR Code dikirim melalui media yang dipilih, seperti WhatsApp atau email.

### 5.2 Check-in dengan QR Code

1. Peserta datang ke lokasi acara.
2. Peserta menunjukkan QR Code dari ponsel atau versi cetak.
3. Panitia membuka halaman scanner.
4. Panitia memindai QR Code.
5. Sistem memvalidasi token dan event terkait.
6. Sistem menampilkan nama peserta dan nama perusahaan.
7. Panitia melakukan verifikasi visual jika diperlukan.
8. Sistem menyimpan waktu check-in dan akun panitia.
9. Sistem menampilkan notifikasi bahwa check-in berhasil.

### 5.3 Peserta Tidak Memiliki QR Code

1. Panitia mencari peserta berdasarkan nama, perusahaan, nomor telepon, atau nomor registrasi.
2. Panitia memverifikasi identitas peserta.
3. Panitia melakukan check-in manual.
4. Sistem mencatat bahwa check-in dilakukan secara manual.
5. Jika dibutuhkan, sistem menerbitkan QR Code baru.

### 5.4 Check-in Ganda

Jika QR Code yang sama dipindai kembali setelah peserta berhasil check-in, sistem harus:

- Menolak pencatatan duplikat.
- Menampilkan status peserta sudah check-in.
- Menampilkan waktu check-in sebelumnya.
- Mencatat percobaan scan pada audit log.

## 6. Fitur Utama

### 6.1 Manajemen Event

Data event meliputi:

- Nama event.
- Logo atau banner.
- Deskripsi acara.
- Tanggal acara.
- Waktu mulai dan selesai.
- Lokasi.
- Batas waktu check-in.
- Status event.

Status event yang disarankan:

| Status | Keterangan |
| --- | --- |
| Draft | Event masih disiapkan dan belum dapat digunakan untuk scan. |
| Aktif | Event sedang berjalan dan dapat menerima check-in. |
| Selesai | Event sudah berakhir dan check-in baru tidak diperbolehkan. |
| Dibatalkan | Event tidak jadi dilaksanakan. |

### 6.2 Manajemen Vendor

Data vendor meliputi:

- Nama perusahaan.
- Kategori vendor.
- Alamat.
- Nama PIC.
- Nomor telepon.
- Email.
- Catatan tambahan.

### 6.3 Manajemen Peserta

Data peserta meliputi:

- Nama lengkap.
- Jabatan.
- Nama perusahaan.
- Nomor telepon.
- Email.
- QR token.
- Status undangan.
- Status kehadiran.
- Waktu check-in.
- Waktu check-out jika fitur tersebut digunakan.

### 6.4 QR Code Personal

Setiap peserta mendapatkan QR Code dengan token unik. QR Code sebaiknya hanya berisi token atau kode registrasi, bukan seluruh data pribadi peserta.

Contoh kode:

```text
VGE-2026-8F4K9X2M
```

Token harus dibuat secara acak dan tidak mudah ditebak. Sistem menggunakan token tersebut untuk mencari data peserta yang sesuai.

### 6.5 Scanner QR Code

Halaman scanner harus menampilkan:

- Preview kamera.
- Nama peserta.
- Nama perusahaan.
- Kategori vendor.
- Foto peserta jika tersedia.
- Status check-in.
- Waktu check-in sebelumnya jika QR Code sudah digunakan.

Notifikasi yang perlu disediakan:

- `Check-in berhasil`.
- `QR Code sudah digunakan`.
- `QR Code tidak valid`.
- `Peserta tidak terdaftar`.
- `Event belum aktif`.
- `Check-in sudah ditutup`.

### 6.6 Pencarian Manual

Pencarian manual digunakan sebagai cadangan apabila peserta tidak dapat menunjukkan QR Code.

Kriteria pencarian:

- Nama peserta.
- Nama perusahaan.
- Nomor telepon.
- Nomor registrasi.

### 6.7 Dashboard

Dashboard minimal menampilkan:

- Total peserta terdaftar.
- Total vendor.
- Total peserta yang hadir.
- Total peserta yang belum hadir.
- Persentase kehadiran.
- Jumlah check-in berdasarkan waktu.
- Daftar check-in terbaru.
- Rekap kehadiran per vendor.

### 6.8 Laporan

Laporan dapat difilter berdasarkan:

- Event.
- Vendor.
- Status kehadiran.
- Rentang waktu check-in.

Format export yang disarankan:

- Excel.
- CSV.
- PDF.

Kolom laporan:

| Kolom | Keterangan |
| --- | --- |
| Nomor | Nomor urut laporan. |
| Nama Peserta | Nama lengkap peserta. |
| Perusahaan | Nama vendor atau perusahaan. |
| Jabatan | Jabatan peserta. |
| Nomor Telepon | Kontak peserta. |
| Status | Status kehadiran. |
| Waktu Check-in | Waktu peserta melakukan check-in. |
| Waktu Check-out | Waktu peserta melakukan check-out jika tersedia. |
| Metode | QR Code atau manual. |
| Petugas | Akun panitia yang memproses absensi. |

## 7. Struktur Halaman

### Halaman Publik

- Halaman informasi event.
- Halaman konfirmasi data peserta.
- Halaman status QR Code.
- Halaman hasil check-in.

### Halaman Admin

- Login.
- Dashboard.
- Daftar event.
- Detail event.
- Daftar vendor.
- Daftar peserta.
- Detail peserta.
- Pembuatan dan pengiriman QR Code.
- Riwayat absensi.
- Laporan.
- Manajemen pengguna.
- Audit log.

### Halaman Panitia

- Scanner QR Code.
- Pencarian peserta.
- Form check-in manual.
- Daftar peserta yang sudah hadir.
- Detail hasil scan.

## 8. Struktur Data

### Tabel `events`

| Field | Keterangan |
| --- | --- |
| `id` | Identitas event. |
| `name` | Nama event. |
| `description` | Deskripsi event. |
| `event_date` | Tanggal pelaksanaan. |
| `start_time` | Waktu mulai. |
| `end_time` | Waktu selesai. |
| `location` | Lokasi event. |
| `status` | Status event. |
| `created_at` | Waktu data dibuat. |
| `updated_at` | Waktu data diperbarui. |

### Tabel `vendors`

| Field | Keterangan |
| --- | --- |
| `id` | Identitas vendor. |
| `company_name` | Nama perusahaan. |
| `category` | Kategori vendor. |
| `address` | Alamat vendor. |
| `contact_name` | Nama PIC. |
| `phone` | Nomor telepon PIC. |
| `email` | Email PIC. |
| `created_at` | Waktu data dibuat. |

### Tabel `participants`

| Field | Keterangan |
| --- | --- |
| `id` | Identitas peserta. |
| `event_id` | Relasi ke event. |
| `vendor_id` | Relasi ke vendor. |
| `name` | Nama peserta. |
| `position` | Jabatan peserta. |
| `phone` | Nomor telepon. |
| `email` | Email peserta. |
| `qr_token` | Token QR Code unik. |
| `invitation_status` | Status undangan. |
| `attendance_status` | Status kehadiran. |
| `check_in_at` | Waktu check-in. |
| `check_out_at` | Waktu check-out. |
| `created_at` | Waktu data dibuat. |
| `updated_at` | Waktu data diperbarui. |

### Tabel `attendance_logs`

| Field | Keterangan |
| --- | --- |
| `id` | Identitas log. |
| `event_id` | Relasi ke event. |
| `participant_id` | Relasi ke peserta. |
| `action` | Jenis aksi, misalnya scan, check-in, atau check-out. |
| `method` | Metode QR Code atau manual. |
| `scanned_by` | Akun petugas. |
| `scanned_at` | Waktu aksi dilakukan. |
| `device_info` | Informasi perangkat jika diperlukan. |
| `notes` | Catatan tambahan. |

## 9. Status Peserta

Status undangan dan kehadiran sebaiknya dipisahkan.

### Status Undangan

```text
Draft
Terkirim
Dikonfirmasi
Dibatalkan
```

### Status Kehadiran

```text
Belum Hadir
Sudah Check-in
Sudah Check-out
Tidak Hadir
```

## 10. Keamanan dan Validasi

- Gunakan token QR Code acak dan sulit ditebak.
- Jangan memasukkan data pribadi lengkap ke dalam QR Code.
- Pastikan token unik untuk setiap peserta pada setiap event.
- Batasi satu check-in untuk satu peserta.
- Validasi bahwa QR Code berasal dari event yang sedang aktif.
- Terapkan batas waktu check-in sesuai konfigurasi event.
- Catat akun petugas, waktu, metode, dan perangkat pada setiap aktivitas.
- Sediakan fitur pembatalan dan penerbitan ulang QR Code.
- Lindungi dashboard dengan autentikasi dan hak akses berbasis role.
- Batasi perubahan waktu kehadiran hanya untuk admin berwenang.
- Simpan audit log dan jangan menghapus histori absensi tanpa otorisasi.
- Gunakan koneksi HTTPS pada lingkungan produksi.
- Validasi seluruh data import untuk mencegah data duplikat atau format tidak valid.

## 11. Skenario Operasional di Lokasi

### Persiapan Panitia

- Pastikan event sudah berstatus aktif.
- Pastikan perangkat panitia memiliki akses kamera.
- Uji scan beberapa QR Code sebelum peserta datang.
- Siapkan koneksi internet cadangan jika memungkinkan.
- Siapkan daftar peserta untuk pencarian manual.
- Siapkan meja atau jalur registrasi sesuai jumlah peserta.

### Jalur Registrasi QR Code

1. Peserta menunjukkan QR Code.
2. Panitia melakukan scan.
3. Sistem menampilkan identitas peserta.
4. Panitia mencocokkan nama atau perusahaan.
5. Sistem menyimpan check-in.
6. Peserta menerima tanda bahwa registrasi berhasil.

### Jalur Registrasi Manual

1. Peserta menyampaikan nama atau perusahaan.
2. Panitia mencari data peserta.
3. Panitia memverifikasi identitas.
4. Panitia mencatat check-in manual.
5. Sistem menyimpan metode check-in sebagai `manual`.

## 12. Rekomendasi MVP

Urutan implementasi yang disarankan:

1. Login dan role admin/panitia.
2. Pembuatan dan pengaturan event.
3. CRUD vendor dan peserta.
4. Import peserta dari Excel atau CSV.
5. Pembuatan QR Code personal.
6. Halaman scanner QR Code.
7. Check-in satu kali.
8. Pencarian dan check-in manual.
9. Dashboard kehadiran.
10. Export laporan.
11. Audit log.

Fitur check-out, RSVP, integrasi WhatsApp, doorprize, dan survey dapat dikembangkan setelah alur MVP stabil.

## 13. Kriteria Keberhasilan

Sistem dianggap memenuhi kebutuhan MVP apabila:

- Admin dapat membuat event dan memasukkan data peserta.
- Setiap peserta memiliki QR Code yang unik.
- Panitia dapat melakukan scan melalui kamera perangkat.
- Sistem menolak QR Code tidak valid dan check-in duplikat.
- Check-in manual tersedia sebagai fallback.
- Status kehadiran dapat dipantau dari dashboard.
- Data dapat diekspor dalam format yang dibutuhkan.
- Seluruh aktivitas absensi memiliki waktu dan petugas yang tercatat.
- Sistem dapat digunakan dengan baik melalui perangkat desktop dan ponsel.

## 14. Rekomendasi Teknologi

Sistem sebaiknya dibuat sebagai aplikasi web responsif agar panitia tidak perlu memasang aplikasi khusus.

Komponen yang diperlukan:

- Frontend web responsif untuk admin dan panitia.
- Backend API untuk autentikasi, event, vendor, peserta, dan absensi.
- Database relasional untuk menyimpan data terstruktur.
- Library scanner QR Code berbasis kamera.
- Library generator QR Code.
- Penyimpanan file untuk logo, foto, atau dokumen jika diperlukan.
- Modul export Excel, CSV, dan PDF.

## 15. Ringkasan Konsep

Konsep yang direkomendasikan adalah sistem absensi berbasis web dengan QR Code personal untuk setiap peserta. Admin mengelola data event dan peserta melalui dashboard, sedangkan panitia menggunakan kamera ponsel untuk melakukan scan di lokasi acara.

MVP difokuskan pada alur inti: registrasi peserta, pembuatan QR Code, validasi scan, pencatatan check-in, dashboard real-time, dan export laporan. Desain ini cukup sederhana untuk diterapkan pada event pertama, tetapi tetap memiliki fondasi yang dapat dikembangkan untuk RSVP, check-out, integrasi pesan, doorprize, dan survey peserta.
