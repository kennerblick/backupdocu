# Installationsscript für BackupDocu (Windows PowerShell)
# Dieses Script installiert BackupDocu von Grund auf neu.
# Es prüft und installiert alle Voraussetzungen, klont das Repository,
# startet die Container und testet den Start.

param(
    [string]$InstallDir = "C:\opt\docker\backupdocu"
)

Write-Host "🚀 Starte BackupDocu-Installation für Windows..."

# Funktion zum Prüfen und Installieren von Programmen (vereinfacht)
function Install-IfMissing {
    param([string]$Command, [string]$InstallCmd)
    if (!(Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-Host "📦 $Command nicht gefunden. Bitte installiere manuell: $InstallCmd"
        exit 1
    } else {
        Write-Host "✅ $Command ist installiert."
    }
}

# 1. Prüfe Docker
Write-Host "🔍 Prüfe Docker..."
Install-IfMissing "docker" "Installiere Docker Desktop von https://www.docker.com/products/docker-desktop"

# 2. Prüfe Git
Write-Host "🔍 Prüfe Git..."
Install-IfMissing "git" "Installiere Git von https://git-scm.com/download/win"

# 3. Erstelle Verzeichnis
Write-Host "📁 Erstelle Verzeichnis $InstallDir..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# 4. Klone Repository
$RepoUrl = "https://github.com/kennerblick/backupdocu.git"
Write-Host "📥 Klone Repository von $RepoUrl..."
Set-Location $InstallDir
if (Test-Path ".git") {
    Write-Host "Repository bereits geklont. Aktualisiere..."
    git pull
} else {
    git clone $RepoUrl .
}

# 5. Prüfe Port-Verfügbarkeit
$DefaultPort = 8080
function Test-Port {
    param([int]$Port)
    $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue
    return $connection.TcpTestSucceeded
}

$Port = $DefaultPort
while (Test-Port $Port) {
    Write-Host "⚠️ Port $Port ist belegt. Versuche nächsten..."
    $Port++
}

Write-Host "✅ Verwende Port $Port"

# Setze Port in .env
if (Test-Path ".env.example") {
    Copy-Item .env.example .env
    (Get-Content .env) -replace 'NGINX_PORT=.*', "NGINX_PORT=$Port" | Set-Content .env
}

# 6. Starte Docker Container
Write-Host "🐳 Starte Docker Container..."
docker compose up -d

# 7. Warte und teste Start
Write-Host "⏳ Warte auf Start..."
Start-Sleep -Seconds 15

$TestUrl = "http://localhost:$Port/api/health"
Write-Host "🧪 Teste BackupDocu unter $TestUrl..."
try {
    $response = Invoke-WebRequest -Uri $TestUrl -TimeoutSec 10
    if ($response.Content -match '"status":"ok"') {
        Write-Host "🎉 BackupDocu erfolgreich gestartet!"
        Write-Host "🌐 Erreichbar unter: http://localhost:$Port"
        Write-Host "📚 API-Dokumentation: http://localhost:$Port/docs"
    } else {
        Write-Host "❌ Fehler beim Start von BackupDocu."
        docker compose logs
        exit 1
    }
} catch {
    Write-Host "❌ Fehler beim Testen: $_"
    docker compose logs
    exit 1
}

Write-Host "✅ Installation abgeschlossen!"