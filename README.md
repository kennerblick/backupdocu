# BackupDocu

Webbasierte Backup-Topologie-Dokumentation für heterogene Server-Infrastrukturen.  
Verwaltet Server, Backup-Quellen, Methoden, Ziele und Jobs – mit interaktivem Flow-Diagramm.

## Features

- **Server-Inventar** – physical, Proxmox-VM, Hyper-V-VM, Container, Cloud
- **Backup-Quellen** – Datenbanken, Shares, Configs, VMs, Kubernetes
- **Backup-Methoden** – Veeam Agent, Veeam B&R, rsync, Bash-Script, pg_dump, PBS
- **Backup-Ziele** – NAS, Tape (LTO-9), Offsite-rsync, Backup-Server, S3
- **Backup-Jobs** – 3-stufig: Primär → Tape → Offsite
- **Flow-Diagramm** – interaktive Visualisierung aller Backup-Pfade
- **Tape & Offsite** – visuell hervorgehoben (orange / cyan)
- **GFS-Policy** – konfigurierbar pro Job
- **Speicheroptionen** – Dateibasiert (JSON, separate Dateien je Collection)
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

```bash
git clone https://github.com/<dein-user>/backupdocu.git
cd backupdocu
cp .env.example .env
# .env anpassen (Passwörter!)
docker compose up -d
```

Danach erreichbar unter: `http://<server-ip>:8080`

API-Dokumentation: `http://<server-ip>:8080/docs`

## Speichermodus

BackupDocu ist jetzt rein JSON-basiert:

- Separate JSON-Dateien im Verzeichnis `backend/data`:
  - `servers.json`
  - `sources.json`
  - `methods.json`
  - `targets.json`
  - `jobs.json`
- Keine Datenbank (PostgreSQL) mehr nötig
- Einfaches Backup/Kopie der Dateien
- Bestehende Strukturen aus der UI werden direkt in diese Dateien geschrieben

**Hinweis:** Der zeitliche Rhythmus (`schedule`), Komprimierung (`is_compressed`) und Verschlüsselung (`is_encrypted`) sind Teil des `jobs`-Objekts.

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
