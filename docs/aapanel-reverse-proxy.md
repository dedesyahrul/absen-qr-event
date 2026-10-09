# Reverse Proxy AAPanel

Dokumen ini menghubungkan domain AAPanel ke Docker proxy aplikasi.

## Prasyarat

Pastikan `.env` aplikasi menggunakan binding lokal berikut:

```dotenv
PUBLIC_BIND_IP=127.0.0.1
HTTPS_PORT=18443
CORS_ORIGINS=https://regist.dedesyahrul.dev
```

Jalankan aplikasi dari root project:

```bash
docker compose up -d --build
docker compose ps
curl -k https://127.0.0.1:18443/api/health
```

Port Docker `18443` hanya boleh listen di `127.0.0.1`. Jangan membuka port tersebut pada firewall publik.

## Konfigurasi VHost AAPanel

Pada AAPanel, buka `Website` > `Configuration` > `配置文件` untuk domain `regist.dedesyahrul.dev`. Pertahankan blok sertifikat dan `well-known` yang dikelola AAPanel, kemudian gunakan konfigurasi reverse proxy berikut.

Bagian `root`, `include enable-php-84.conf`, rewrite PHP, dan location static dari template PHP tidak diperlukan dan sebaiknya dihapus atau dikomentari. Jika dibiarkan, regex location static/PHP dapat mengambil alih request frontend sebelum diteruskan ke Docker.

```nginx
server {
    listen 80;
    listen 443 ssl;
    listen 443 quic;
    http2 on;
    http3 on;
    server_name regist.dedesyahrul.dev;

    # Tetap gunakan sertifikat yang dikelola AAPanel.
    ssl_certificate /www/server/panel/vhost/cert/regist.dedesyahrul.dev/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/regist.dedesyahrul.dev/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Redirect HTTP ke HTTPS. Sertifikat tetap diterminasi di AAPanel.
    if ($scheme = http) {
        return 301 https://$host$request_uri;
    }

    client_max_body_size 20M;

    # Docker proxy menggunakan sertifikat self-signed internal.
    # TLS publik tetap menggunakan sertifikat AAPanel di atas.
    proxy_ssl_verify off;

    location / {
        proxy_pass https://127.0.0.1:18443;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port 443;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_buffering off;
    }

    # Jangan expose file sensitif dari document root AAPanel.
    location ~ ^/(\.env|\.git|\.svn|\.htaccess|\.user\.ini|README\.md|LICENSE) {
        return 404;
    }

    # Biarkan AAPanel melakukan verifikasi sertifikat ACME.
    location ^~ /.well-known/ {
        root /www/wwwroot/regist.dedesyahrul.dev;
        allow all;
    }

    access_log /www/wwwlogs/regist.dedesyahrul.dev.log;
    error_log /www/wwwlogs/regist.dedesyahrul.dev.error.log;
}
```

## Catatan Konfigurasi

- Jangan menambahkan `location /api/` terpisah dengan `proxy_pass` lain. Docker proxy sudah meneruskan `/api/` ke backend internal.
- Jangan memakai `include enable-php-84.conf` pada vhost ini karena aplikasi bukan PHP.
- Jangan memakai `root` sebagai sumber halaman utama. Halaman Vue disajikan oleh container frontend.
- `proxy_ssl_verify off` hanya berlaku untuk koneksi lokal AAPanel ke Docker proxy self-signed, bukan untuk koneksi publik pengguna.
- Jika ingin menghilangkan `proxy_ssl_verify off`, gunakan sertifikat internal yang dipercaya AAPanel atau ubah Docker proxy menjadi HTTP lokal.

## Terapkan Dan Uji

Setelah menyimpan konfigurasi pada AAPanel:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Uji dari VPS:

```bash
curl -I https://regist.dedesyahrul.dev
curl -fsS https://regist.dedesyahrul.dev/api/health
```

Uji port Docker hanya melalui loopback:

```bash
ss -lntp | grep 18443
```

Output yang benar harus menunjukkan `127.0.0.1:18443`, bukan `0.0.0.0:18443`.

## Jika Muncul 502 Bad Gateway

Periksa service Docker:

```bash
docker compose ps
docker compose logs --tail 100 proxy
docker compose logs --tail 100 backend
```

Periksa koneksi langsung dari host:

```bash
curl -vk https://127.0.0.1:18443/api/health
```

Jika koneksi langsung berhasil tetapi domain menghasilkan 502, periksa konfigurasi AAPanel dan pastikan `proxy_pass` menggunakan `https://127.0.0.1:18443` serta `proxy_ssl_verify off` berada pada context `server` atau `location` yang aktif.
