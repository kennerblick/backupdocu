# BackupDocu

Webbasierte Backup-Topologie-Dokumentation für heterogene Server-Infrastrukturen.  
Verwaltet Server, Backup-Quellen, Methoden, Targets und Jobs mit server-spezifischer Datenablage, Tree-View, Topologie-Ansicht und versionierter Konfiguration über `config-data`.

## Features

- **Server-Inventar** – physical, Proxmox-VM, Hyper-V-VM, Container, Cloud
- **Standort-Management** – Standort pro Server  filterbar und gruppiert in der Server-Ansicht
- **Server-Funktionen** – u. a. `Webserver`, `SFTP-Server`, `Share`, `DNS`, `DHCP`, `Router`
- **Virtualisierung als eigenes Feld** – auswählbar: `HyperV`, `Docker`, `Proxmox`, `Kubernetes`, `VMware`
- **Backup-Quellen** – Datenbanken, Shares, Configs, VMs, Kubernetes; direkt im Server-Editor pflegbar
- **Backup-Methoden** – local backupagent, central backup mgmt, rsync, Bash-Script, db-dump, Tape Job
- **Targets** – eigene Hauptmenü-Ansicht für Backup-Ziele (NAS, Tape, Offsite, Backup-Server, S3)
- **Backup-Flow** – serverbezogene Ansicht für Quellen und Jobs
- **Backup-Jobs** – 3-stufig: Primär → Tape → Offsite
- **1-Click Job-Erstellung** – Linux-Schnellkonfiguration für Systembackup und DB-Dump (Standard: täglich, Aufbewahrung 3 Tage)
- **Topologie-Ansicht** – interaktive Visualisierung Server → Quelle → Job → Methode → Target
- **Tree-View** – nur Server mit Quellen, direkt editierbare Einträge
- **Tape & Offsite** – visuell hervorgehoben (orange / cyan)
- **Speicheroptionen** – dateibasiert (JSON, per-server Verzeichnisse + versioniertes `config-data`)

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

Danach erreichbar unter: `http://<server-ip>:9090`  
(oder dem in `NGINX_PORT` gesetzten Port)

API-Dokumentation: `http://<server-ip>:9090/docs`

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

BackupDocu ist rein JSON-basiert und trennt **Betriebsdaten** von **versionierter Konfiguration**:

- **Laufende Betriebsdaten** im Verzeichnis `data` (Host) bzw. `/app/data` (Container):
  - `servers.json`
  - `targets.json`
  - `settings.json`
  - `servers/<server_id>/sources.json`
  - `servers/<server_id>/jobs.json`
- **Versionierte Konfiguration** im Verzeichnis `backend/config-data` bzw. `/app/config-data`:
  - `backup-methods.json`
  - `backup-types.json`
  - `virtualization-types.json`

Vorteile:
- Keine Datenbank nötig
- Einfaches Backup/Kopie von `data/`
- Konfigurierbare Typen und Methoden können normal über Git gepusht/gepullt werden
- Bestehende Strukturen aus der UI werden direkt in JSON-Dateien geschrieben

**Wichtig für Deployments:**
- Betriebsdaten liegen im gemounteten Verzeichnis `./data`.
- Dieses Verzeichnis sollte nicht über Git versioniert/überschrieben werden.
- Vor Updates empfiehlt sich ein Backup von `data/`.

**Hinweis:** Zeitplan (`schedule`), Komprimierung (`is_compressed`) und Verschlüsselung (`is_encrypted`) sind Teil des `jobs`-Objekts.

## UI-Ansichten und Skalierung

Die Hauptnavigation ist aktuell in folgende Bereiche gegliedert:

- **Topologie** – grafische Gesamtansicht aller Server, Quellen, Jobs, Methoden und Targets
- **Server** – gruppiert nach Standort, mit direkter Bearbeitung und scrollbarer Listenansicht
- **Baum** – reduzierte Strukturansicht, nur Server mit Quellen
- **Targets** – zentrale Pflege aller Backup-Ziele
- **Backup-Flow** – serverbezogene Verwaltung von Quellen und Jobs

Für größere Umgebungen (z. B. 60+ Server) bietet die Server-Verwaltung zusätzlich:

- Filter nach **Standort**
- Gruppierung der Tabelle nach **Standort** inkl. Anzahl je Gruppe
- Eigenes Feld **Virtualisierung**
- Direkte Quellenpflege direkt im Server-Editor
- Vertikale Scrollbarkeit bei langen Listen

## Relevante API-Endpunkte

- `GET /api/servers`, `POST /api/servers`, `PUT /api/servers/{id}`, `DELETE /api/servers/{id}`
- `GET /api/servers/{id}/sources`, `POST /api/servers/{id}/sources`, `PUT /api/servers/{id}/sources/{sid}`, `DELETE /api/servers/{id}/sources/{sid}`
- `GET /api/servers/{id}/jobs`, `POST /api/servers/{id}/jobs`, `PUT /api/servers/{id}/jobs/{jid}`, `DELETE /api/servers/{id}/jobs/{jid}`
- `GET /api/methods`
- `GET /api/targets`, `POST /api/targets`, `PUT /api/targets/{id}`, `DELETE /api/targets/{id}`
- `GET /api/backup-types`
- `GET /api/virtualization-types`
- `GET /api/server-functions`, `POST /api/server-functions`, `PUT /api/server-functions/{id}`, `DELETE /api/server-functions/{id}`
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
  proxy_pass http://localhost:9090/;
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
