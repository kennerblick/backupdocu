#!/bin/bash
# Installationsscript für BackupDocu
# Dieses Script installiert BackupDocu von Grund auf neu.
# Es prüft und installiert alle Voraussetzungen, klont das Repository,
# startet die Container und testet den Start.

set -e  # Script beenden bei Fehlern

echo "🚀 Starte BackupDocu-Installation..."

# Funktion zum Prüfen und Installieren von Paketen
install_if_missing() {
    local package=$1
    if ! command -v $package &> /dev/null; then
        echo "📦 Installiere $package..."
        apt update && apt install -y $package
    else
        echo "✅ $package ist bereits installiert."
    fi
}

# 1. Prüfe und installiere Docker
echo "🔍 Prüfe Docker..."
if ! command -v docker &> /dev/null; then
    echo "📦 Docker nicht gefunden. Installiere docker.io..."
    apt update
    apt install -y docker.io
    systemctl start docker
    systemctl enable docker
    echo "✅ Docker installiert und gestartet."
else
    echo "✅ Docker ist bereits installiert."
fi

# 2. Prüfe und installiere Git
install_if_missing git

# 3. Prüfe und installiere curl (für Tests)
install_if_missing curl

# 4. Erstelle Verzeichnis
INSTALL_DIR="/opt/docker/backupdocu"
echo "📁 Erstelle Verzeichnis $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# 5. Klone Repository
REPO_URL="https://github.com/kennerblick/backupdocu.git"
echo "📥 Klone Repository von $REPO_URL..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Repository bereits geklont. Aktualisiere..."
    cd "$INSTALL_DIR"
    git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 6. Prüfe Port-Verfügbarkeit
DEFAULT_PORT=8080
check_port() {
    local port=$1
    if ss -tuln | grep -q ":$port "; then
        return 1  # Port belegt
    else
        return 0  # Port frei
    fi
}

PORT=$DEFAULT_PORT
while ! check_port $PORT; do
    echo "⚠️ Port $PORT ist belegt. Versuche nächsten..."
    ((PORT++))
done

echo "✅ Verwende Port $PORT"

# Setze Port in .env falls nötig
if [ -f ".env.example" ]; then
    cp .env.example .env
    sed -i "s/NGINX_PORT=.*/NGINX_PORT=$PORT/" .env
fi

# 7. Starte Docker Container
echo "🐳 Starte Docker Container..."
docker compose up -d

# 8. Warte und teste Start
echo "⏳ Warte auf Start..."
sleep 10

TEST_URL="http://localhost:$PORT/api/health"
echo "🧪 Teste BackupDocu unter $TEST_URL..."
if curl -s --max-time 10 "$TEST_URL" | grep -q '"status":"ok"'; then
    echo "🎉 BackupDocu erfolgreich gestartet!"
    echo "🌐 Erreichbar unter: http://localhost:$PORT"
    echo "📚 API-Dokumentation: http://localhost:$PORT/docs"
else
    echo "❌ Fehler beim Start von BackupDocu. Prüfe Logs:"
    docker compose logs
    exit 1
fi

echo "✅ Installation abgeschlossen!"