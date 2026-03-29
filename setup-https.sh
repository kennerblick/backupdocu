#!/bin/bash
# HTTPS/SSL Setup für BackupDocu mit Let's Encrypt
# Dieses Script konfiguriert SSL-Zertifikate automatisch via Certbot

set -e

INSTALL_DIR="/opt/docker/backupdocu"
DOMAIN=${1:-localhost}

echo "🔐 Konfiguriere HTTPS/SSL für BackupDocu..."

# Prüfe ob Certbot installiert ist
if ! command -v certbot &> /dev/null; then
    echo "📦 Installiere Certbot für Let's Encrypt..."
    apt update && apt install -y certbot python3-certbot-nginx
else
    echo "✅ Certbot ist installiert."
fi

# Erstelle Verzeichnis für Zertifikate
mkdir -p "$INSTALL_DIR/letsencrypt"
mkdir -p "$INSTALL_DIR/certbot"

cd "$INSTALL_DIR"

# Für Test: Self-signed Certificate erstellen (schnell, aber nicht für Produktion)
if [ "$DOMAIN" = "localhost" ] || [ "$DOMAIN" = "127.0.0.1" ]; then
    echo "⚠️ Erstelle Self-Signed Certificate für Localhost (nur für Tests!)"
    mkdir -p ./letsencrypt/live/backupdocu
    openssl req -x509 -newkey rsa:4096 -keyout ./letsencrypt/live/backupdocu/privkey.pem -out ./letsencrypt/live/backupdocu/fullchain.pem -days 365 -nodes -subj "/CN=localhost"
    echo "✅ Self-signed Certificate erstellt."
else
    echo "🌐 Verwende Let's Encrypt für Domain: $DOMAIN"
    # Prüfe Port 80 Verfügbarkeit
    if ss -tuln | grep -q ":80 "; then
        echo "❌ Port 80 ist belegt. Bitte freigeben für Certbot."
        exit 1
    fi
    # Starte Container nur mit HTTP für Certbot
    echo "🚀 Starte nginx für Certbot-Challenge..."
    docker compose up -d nginx
    sleep 5
    # Lass Certbot das Zertifikat holen
    certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos -m admin@$DOMAIN
    echo "✅ Let's Encrypt Zertifikat erhalten."
fi

# Erstelle HTTPS-Konfigurationsdatei
cat > "$INSTALL_DIR/nginx/https.conf" << 'EOF'
server {
    listen 443 http2 ssl;
    listen [::]:443 http2 ssl;
    server_name _;

    ssl_certificate /etc/letsencrypt/live/backupdocu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/backupdocu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    location /docs {
        proxy_pass http://backend:8000/docs;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://backend:8000/openapi.json;
    }

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
}
EOF

cat > "$INSTALL_DIR/nginx/http-redirect.conf" << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    location / {
        return 301 https://$host$request_uri;
    }
}
EOF

echo "✅ HTTPS-Konfigurationsdateien erstellt."