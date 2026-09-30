#!/bin/sh
CERT_DIR="/etc/nginx/certs"

if [ ! -f "$CERT_DIR/selfsigned.crt" ] || [ ! -f "$CERT_DIR/selfsigned.key" ]; then
    echo "Generating self-signed SSL certificate..."
    apk add --no-cache openssl > /dev/null 2>&1
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout "$CERT_DIR/selfsigned.key" \
        -out "$CERT_DIR/selfsigned.crt" \
        -subj "/C=ID/ST=Jakarta/L=Jakarta/O=Gatherly/CN=gatherly.local"
    echo "SSL certificate generated."
else
    echo "SSL certificate already exists, skipping generation."
fi

exec nginx -g "daemon off;"
