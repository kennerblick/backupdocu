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

# Verzeichnisrechte
chmod -R 755 ./letsencrypt
chmod -R 755 ./certbot

echo "🔄 Starte Docker Container mit HTTPS neu..."
docker compose down
docker compose up -d

echo "✅ HTTPS/SSL Setup abgeschlossen!"
echo "🌐 Erreichbar unter: https://$DOMAIN"
echo "⚠️ Bei Self-Signed Cert: Browser-Warnung akzeptieren (sicher, aber nicht öffentlich)"