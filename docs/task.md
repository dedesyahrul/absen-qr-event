# UI/UX Improvement — Event Registration & Check-in System

Saya ingin melakukan **perbaikan dan penyempurnaan UI/UX** pada aplikasi yang sudah ada.

## 1. Brand & Identitas Aplikasi

Gunakan nama brand resmi:

**Event Registration & Check-in System**

Domain aplikasi:

**regist.dedesyahrul.dev**

Nama brand tersebut harus digunakan secara konsisten pada elemen UI yang relevan, seperti:

* Browser title
* Login page
* Navbar / header
* Sidebar
* Dashboard
* Footer jika ada
* Empty state / landing state jika relevan

Jangan menggunakan nama brand lama jika masih terdapat pada UI.

Untuk penyebutan singkat di area yang membutuhkan ruang terbatas, dapat menggunakan:

**Event Registration**

Namun pada area utama/branding tetap gunakan:

**Event Registration & Check-in System**

Domain **regist.dedesyahrul.dev** dapat digunakan sebagai identitas aplikasi jika memang relevan secara visual, tetapi jangan menjadikan domain sebagai brand utama.

---

# 2. Fokus Utama

Tugas utama adalah:

> **Improve the existing UI/UX without changing the application's backend, business logic, API, database, authentication flow, or existing functionality.**

Saya hanya meminta perubahan pada **presentation layer / frontend UI/UX**.

Prioritaskan:

* Visual hierarchy
* Layout
* Spacing
* Typography
* Color system
* Component consistency
* Navigation
* Form usability
* Table usability
* Button hierarchy
* Status/badge
* Empty state
* Loading state
* Error state
* Responsive design
* Accessibility
* Overall user experience

---

# 3. BAHASA UI

Gunakan **Bahasa Indonesia dengan gaya corporate/profesional**.

Bahasa harus:

* Natural
* Ringkas
* Jelas
* Profesional
* Tidak terlalu formal/kaku
* Cocok untuk penggunaan perusahaan dan event

Hindari penggunaan bahasa yang terlalu teknis atau terasa seperti hasil terjemahan mesin.

Contoh:

❌ "Create New Event"

✅ "Buat Event"

❌ "No data available"

✅ "Belum ada data"

❌ "Are you sure you want to delete this?"

✅ "Apakah Anda yakin ingin menghapus data ini?"

❌ "Submit Registration"

✅ "Daftar"

❌ "Check In Participant"

✅ "Check-in Peserta"

Gunakan istilah yang konsisten di seluruh aplikasi.

---

# 4. Gaya Visual

Buat tampilan yang memberikan kesan:

**Modern Corporate Event Management**

Karakter UI:

* Clean
* Modern
* Professional
* Minimal
* Elegant
* Tidak terlalu ramai
* Tidak terlihat seperti template admin dashboard generik
* Nyaman digunakan dalam event dengan jumlah peserta yang banyak

Jangan menggunakan terlalu banyak:

* Gradient
* Shadow berat
* Border berlebihan
* Animasi berlebihan
* Warna mencolok
* Decorative elements yang tidak memiliki fungsi

Prioritaskan **clarity dan usability**.

---

# 5. Design System

Buat/rapikan design system yang konsisten untuk seluruh aplikasi.

Perhatikan:

### Typography

Gunakan font modern dan profesional yang mudah dibaca.

Buat hierarchy yang jelas untuk:

* Page title
* Section title
* Subtitle
* Body text
* Label
* Caption
* Table text
* Button text

### Spacing

Gunakan spacing yang konsisten.

Hindari:

* Elemen terlalu berdempetan
* Elemen terlalu jauh
* Padding yang tidak konsisten antar halaman

### Button

Buat hierarchy:

**Primary**

* Aksi utama seperti "Buat Event", "Simpan", "Check-in"

**Secondary**

* Aksi alternatif seperti "Batal", "Kembali"

**Danger**

* Hapus
* Batalkan
* Nonaktifkan

Pastikan button memiliki ukuran, radius, typography, dan icon yang konsisten.

### Badge / Status

Gunakan status yang mudah dipahami, misalnya:

* Aktif
* Draft
* Selesai
* Belum Check-in
* Sudah Check-in
* Dibatalkan

Jangan hanya mengandalkan warna. Gunakan text/status yang jelas.

---

# 6. Dashboard

Jika aplikasi memiliki dashboard, perbaiki agar pengguna dapat memahami kondisi event dengan cepat.

Prioritaskan informasi seperti:

* Total Event
* Event Aktif
* Total Peserta
* Sudah Check-in
* Belum Check-in

Gunakan card/statistic component yang sederhana dan informatif.

Jangan membuat dashboard terlalu ramai.

Jika terdapat event yang sedang berlangsung, berikan visual priority pada event tersebut.

---

# 7. Event Management

Perbaiki UX untuk pengelolaan event.

Informasi penting harus mudah ditemukan:

* Nama Event
* Tanggal
* Lokasi
* Status
* Jumlah Peserta
* Check-in
* Action

Gunakan hierarchy yang jelas.

Action yang umum seperti:

* Lihat Detail
* Edit
* Kelola Peserta
* Check-in
* QR Code

sebaiknya mudah ditemukan tetapi tidak membuat interface terlihat penuh.

---

# 8. Registrasi Peserta

Form registrasi harus terasa sederhana dan cepat.

Kelompokkan field berdasarkan konteks.

Contoh:

### Informasi Peserta

* Nama Lengkap
* Email
* Nomor HP

### Informasi Perusahaan

* Nama Perusahaan
* Jabatan
* Divisi

### Informasi Event

* Event
* Kategori Peserta

Gunakan:

* Label yang jelas
* Placeholder seperlunya
* Validation message yang mudah dipahami
* Required indicator yang konsisten

Jangan membuat user mengisi informasi yang tidak diperlukan.

---

# 9. Check-in

Check-in merupakan salah satu fungsi utama aplikasi sehingga UX-nya harus sangat cepat.

Prioritaskan:

**Scan / input → Identifikasi peserta → Konfirmasi → Check-in berhasil**

Gunakan visual feedback yang jelas.

Contoh status:

**Check-in Berhasil**

> Peserta berhasil melakukan check-in.

atau:

**Peserta Tidak Ditemukan**

> Data peserta tidak ditemukan. Silakan periksa kembali QR Code atau data registrasi.

Jangan membuat proses check-in menjadi rumit.

---

# 10. QR Code

Jika terdapat QR Code peserta:

* Pastikan QR Code memiliki ruang yang cukup
* Jangan terlalu banyak elemen dekoratif di sekitar QR
* Pastikan QR mudah dipindai
* Gunakan hierarchy yang jelas
* Informasi penting tetap terlihat

Jika terdapat halaman QR peserta, gunakan branding:

**Event Registration & Check-in System**

dan event name sebagai informasi utama.

---

# 11. Table

Perbaiki table agar nyaman digunakan pada data peserta dalam jumlah besar.

Prioritaskan:

* Search
* Filter
* Sorting
* Pagination
* Status
* Action

Gunakan sticky header jika memang dibutuhkan.

Jangan membuat setiap kolom terlalu lebar.

Untuk action yang banyak, gunakan dropdown/menu agar tidak memenuhi table.

---

# 12. Responsive Design

Pastikan UI nyaman digunakan pada:

* Desktop
* Laptop
* Tablet
* Mobile

Untuk mobile, jangan sekadar mengecilkan desktop UI.

Lakukan responsive adaptation yang benar.

Contoh:

* Table → card/list pada mobile jika diperlukan
* Sidebar → mobile navigation
* Form → single column
* Button → full width jika sesuai
* Statistic cards → responsive grid

---

# 13. Empty State

Buat empty state yang informatif.

Contoh:

**Belum Ada Event**

> Belum ada event yang tersedia. Silakan buat event baru untuk memulai.

CTA:

**+ Buat Event**

Jangan menggunakan empty state yang hanya menampilkan:

"No Data"

---

# 14. Loading & Feedback

Gunakan loading state yang baik.

Hindari halaman terasa "freeze".

Gunakan:

* Skeleton
* Spinner
* Loading indicator
* Toast
* Success feedback
* Error feedback

Feedback harus menggunakan Bahasa Indonesia.

Contoh:

**Data berhasil disimpan**

**Data berhasil diperbarui**

**Terjadi kesalahan. Silakan coba kembali.**

---

# 15. Login

Jika terdapat halaman login, redesign agar terlihat sebagai produk yang memiliki identitas sendiri.

Gunakan:

**Event Registration & Check-in System**

sebagai brand utama.

Tambahkan deskripsi singkat jika diperlukan:

> Platform untuk mengelola registrasi dan check-in peserta event.

Tetap sederhana dan corporate.

---

# 16. Navigation

Rapikan navigation/sidebar.

Gunakan struktur yang mudah dipahami.

Contoh:

**Dashboard**

**Event**

* Daftar Event
* Buat Event

**Peserta**

* Daftar Peserta
* Registrasi

**Check-in**

**Laporan**

**Pengaturan**

Sesuaikan dengan menu yang memang sudah tersedia.

**Jangan membuat fitur backend baru hanya karena contoh menu di atas.**

Jika fitur tersebut belum tersedia, jangan membuat logic baru.

---

# 17. Important — DO NOT CHANGE BACKEND

Ini adalah bagian paling penting.

**JANGAN mengubah backend.**

Jangan:

* Mengubah API
* Mengubah endpoint
* Mengubah database
* Mengubah schema database
* Mengubah model
* Mengubah authentication logic
* Mengubah authorization logic
* Mengubah business logic
* Mengubah validation backend
* Mengubah query
* Mengubah API response
* Mengubah struktur data
* Mengubah proses registrasi yang sudah berjalan
* Mengubah proses check-in yang sudah berjalan

Gunakan **existing API dan existing data**.

Jika UI membutuhkan data tertentu yang belum tersedia dari backend:

> Jangan membuat backend baru.

Gunakan data yang sudah tersedia atau lakukan improvement hanya pada presentation layer.

---

# 18. DO NOT BREAK EXISTING FUNCTIONALITY

Sebelum melakukan perubahan:

1. Inspect existing project structure.
2. Identifikasi frontend dan backend.
3. Identifikasi framework/component library yang digunakan.
4. Identifikasi halaman yang tersedia.
5. Identifikasi reusable components.
6. Identifikasi existing API integration.
7. Pahami flow existing application.

Kemudian lakukan perubahan seminimal mungkin terhadap architecture.

**Reuse existing components dan logic jika memungkinkan.**

Jangan melakukan rewrite besar-besaran hanya demi UI.

---

# 19. UI/UX Consistency

Pastikan semua halaman memiliki visual language yang sama.

Perhatikan konsistensi:

* Button
* Input
* Select
* Modal
* Dialog
* Toast
* Table
* Card
* Badge
* Icon
* Typography
* Spacing
* Border radius
* Shadow
* Color
* Page header
* Breadcrumb

Jangan sampai setiap halaman terlihat dibuat dengan style yang berbeda.

---

# 20. Final Objective

Hasil akhirnya harus terasa seperti sebuah produk corporate yang benar-benar siap digunakan untuk event.

Brand:

**Event Registration & Check-in System**

Domain:

**regist.dedesyahrul.dev**

Target UX:

> **Cepat, jelas, modern, profesional, dan mudah digunakan oleh panitia maupun peserta event.**

Sekali lagi:

**Fokus hanya pada UI/UX/frontend presentation.**

**Jangan mengubah backend, API, database, business logic, authentication, atau functionality yang sudah berjalan.**
