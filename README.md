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
- **Speicheroptionen** – JSON-Dateien (default) oder PostgreSQL-Datenbank
- **Export/Import** – komplette Konfiguration als JSON

## Stack

| Komponente | Technologie |
|------------|-------------|
| Frontend | Vanilla HTML/JS + vis-network.js |
| Backend | FastAPI (Python 3.12) |
| Datenbank | PostgreSQL 16 (optional) |
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

BackupDocu unterstützt zwei Speichermodi:

### JSON-Modus (Default)
- Speichert alle Daten in `backend/storage.json`
- Keine Datenbank-Abhängigkeit
- Ideal für kleine Setups oder Tests
- Automatische Datei-Erstellung

### Datenbank-Modus
- Verwendet PostgreSQL für persistente Speicherung
- Mehrere Benutzer / Skalierbarkeit
- Setze `STORAGE_MODE=db` in `.env`

**Modus-Wechsel:** In der Web-UI über "Speichermodus" Dropdown umschalten.

## CI/CD

GitHub Actions testet automatisch beide Speichermodi:

- **JSON-Modus:** CRUD-Operationen ohne Datenbank
- **DB-Modus:** PostgreSQL-Integration mit vollem CRUD

```bash
# Lokaler Test
STORAGE_MODE=json uvicorn backend.main:app --reload
STORAGE_MODE=db uvicorn backend.main:app --reload
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
