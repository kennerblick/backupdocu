# BackupDocu

Webbasierte Backup-Topologie-Dokumentation für heterogene Server-Infrastrukturen.  
Verwaltet Server, Backup-Quellen, Methoden, Ziele und Jobs mit server-spezifischer Datenablage, Tree-View und interaktivem Flow-Diagramm.

## Features

- **Server-Inventar** – physical, Proxmox-VM, Hyper-V-VM, Container, Cloud
- **Standort-Management** – Standort pro Server (`extern`, `gruenes Netz`, `gelbes Netz`, `virtuell`), filterbar und gruppiert in der Server-Ansicht
- **Backup-Quellen** – Datenbanken, Shares, Configs, VMs, Kubernetes
- **Backup-Methoden** – Veeam Agent, Veeam B&R, rsync, Bash-Script, pg_dump, PBS
- **Backup-Ziele** – NAS, Tape (LTO-9), Offsite-rsync, Backup-Server, S3
- **Backup-Jobs** – 3-stufig: Primär → Tape → Offsite
- **1-Click Job-Erstellung** – Linux-Schnellkonfiguration für Systembackup und DB-Dump (Standard: täglich, Aufbewahrung 3 Tage)
- **Flow-Diagramm** – interaktive Visualisierung aller Backup-Pfade
- **Tree-View** – nur Server mit Quellen, direkt editierbare Einträge
- **Tape & Offsite** – visuell hervorgehoben (orange / cyan)
- **GFS-Policy** – konfigurierbar pro Job
- **Speicheroptionen** – Dateibasiert (JSON, per-server Verzeichnisse)
- **Export/Import** – komplette Konfiguration als JSON

## Stack

| Komponente | Technologie |
|------------|-------------|
| Frontend | Vanilla HTML/JS + vis-network.js |
| Backend | FastAPI (Python 3.12) |
| Speicher | JSON-Dateien (lokales Dateisystem) |
| Web-Server | nginx |
| Deployment | Docker Compose |

## Schnellstart

### Automatische Installation

Für eine vollständige Installation von Grund auf (inkl. Docker/Git-Prüfung und -Installation):

**Linux (Bash):**
```bash
curl -fsSL https://raw.githubusercontent.com/kennerblick/backupdocu/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/kennerblick/backupdocu/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

### Manuell

```bash
git clone https://github.com/<dein-user>/backupdocu.git
cd backupdocu
cp .env.example .env
# .env anpassen (Passwörter!)
docker compose up -d
```

Danach erreichbar unter: `http://<server-ip>:8080`

API-Dokumentation: `http://<server-ip>:8080/docs`

## HTTPS/SSL Setup

BackupDocu unterstützt HTTPS mit minimalem Aufwand:

### Option 1: Let's Encrypt (Produktion)
```bash
# Für eine Domain (z.B. backupdocu.example.com)
chmod +x setup-https.sh
./setup-https.sh backupdocu.example.com
```

Das Script:
- Verlangt automatisch ein kostenloses Zertifikat von Let's Encrypt
- Configured nginx für HTTPS
- Container automatisch mit SSL neu starten
- Zertifikat auto-erneuert sich

### Option 2: Self-Signed (Tests/Intern)
```bash
./setup-https.sh localhost
```

Erstellt ein selbstsigniertes Zertifikat (schnell, aber Browser-Warnung).

### Manuell
nginx lädt Zertifikate von:
- `/opt/docker/backupdocu/letsencrypt/live/backupdocu/fullchain.pem`
- `/opt/docker/backupdocu/letsencrypt/live/backupdocu/privkey.pem`

Kopiere deine Zertifikate dorthin, nginx lädt sie automatisch beim Neustart.

BackupDocu ist rein JSON-basiert:

- Separate JSON-Dateien im Verzeichnis `data` (Host) bzw. `/app/data` (Container):
  - `servers.json`
  - `methods.json`
  - `targets.json`
  - `settings.json`
  - `servers/<server_id>/sources.json`
  - `servers/<server_id>/jobs.json`
- Keine Datenbank (PostgreSQL) mehr nötig
- Einfaches Backup/Kopie der Dateien
- Bestehende Strukturen aus der UI werden direkt in diese Dateien geschrieben

**Wichtig für Deployments:**
- Betriebsdaten liegen im gemounteten Verzeichnis `./data`.
- Dieses Verzeichnis sollte nicht über Git versioniert/überschrieben werden.
- Vor Updates empfiehlt sich ein Backup von `data/`.

**Hinweis:** Der zeitliche Rhythmus (`schedule`), Komprimierung (`is_compressed`) und Verschlüsselung (`is_encrypted`) sind Teil des `jobs`-Objekts.

## Server-Ansicht (Skalierung)

Für größere Umgebungen (z. B. 60+ Server) bietet die Server-Verwaltung:

- Filter nach **Standort**
- Gruppierung der Tabelle nach **Standort** inkl. Anzahl je Gruppe
- Direkte Bearbeitung aus der Übersicht

Dadurch bleiben große Inventare übersichtlich und schneller navigierbar.

## Relevante API-Endpunkte

- `GET /api/servers`, `POST /api/servers`, `PUT /api/servers/{id}`, `DELETE /api/servers/{id}`
- `GET /api/servers/{id}/sources`, `POST /api/servers/{id}/sources`, `PUT /api/servers/{id}/sources/{sid}`, `DELETE /api/servers/{id}/sources/{sid}`
- `GET /api/servers/{id}/jobs`, `POST /api/servers/{id}/jobs`, `PUT /api/servers/{id}/jobs/{jid}`, `DELETE /api/servers/{id}/jobs/{jid}`
- `GET /api/server-functions`
- `GET /api/server-locations`, `POST /api/server-locations`, `PUT /api/server-locations/{id}`, `DELETE /api/server-locations/{id}`
- `GET /api/stats`, `GET /api/health`

## CI/CD

GitHub Actions testet automatisch den JSON-Speichermodus:

- **JSON-Modus:** CRUD-Operationen ohne Datenbank

```bash
# Lokaler Test
uvicorn backend.main:app --reload
```

## Datenmodell

```
Server
  └─► BackupSource (1:n)
           └─► BackupJob
                    ├─► BackupMethod
                    ├─► BackupTarget (Primär)
                    ├─► BackupTarget (Tape, optional)
                    └─► BackupTarget (Offsite, optional)
```

## Produktions-Deployment (hinter eigenem nginx / FreeIPA)

Für den Einsatz hinter einem bestehenden nginx Reverse-Proxy empfiehlt sich:

```nginx
location /backupdocu/ {
    proxy_pass http://localhost:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Entwicklung

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Lizenz

MIT
