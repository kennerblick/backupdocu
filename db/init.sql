-- BackupDocu Database Schema

CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    hostname VARCHAR(255),
    type VARCHAR(50) DEFAULT 'physical',  -- physical, vm-proxmox, vm-hyperv, container, cloud
    os VARCHAR(100),
    role TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backup_targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- local, nas, backup-server, tape-lto9, offsite-rsync, s3
    hostname VARCHAR(255),
    path TEXT,
    capacity_tb NUMERIC(10,2),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backup_sources (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- share, database, config, vm-full, system, kubernetes
    path TEXT,
    size_gb NUMERIC(12,2),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backup_methods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- veeam-agent, veeam-br, rsync, bash-script, pg_dump, tar, zabbix-config
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backup_jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    source_id INTEGER REFERENCES backup_sources(id) ON DELETE CASCADE,
    method_id INTEGER REFERENCES backup_methods(id),
    primary_target_id INTEGER REFERENCES backup_targets(id),
    tape_target_id INTEGER REFERENCES backup_targets(id),  -- optional 2nd tier: tape
    offsite_target_id INTEGER REFERENCES backup_targets(id), -- optional 3rd tier: offsite
    schedule VARCHAR(200),        -- human-readable or cron
    retention VARCHAR(200),
    gfs_policy VARCHAR(200),      -- e.g. "7 daily, 4 weekly, 12 monthly"
    is_encrypted BOOLEAN DEFAULT FALSE,
    is_compressed BOOLEAN DEFAULT TRUE,
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, disabled
    last_run TIMESTAMPTZ,
    last_result VARCHAR(50),      -- success, warning, failed, unknown
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER servers_updated_at BEFORE UPDATE ON servers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER backup_jobs_updated_at BEFORE UPDATE ON backup_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── Seed data (AV-Test style example) ─────────────────────────────────────

INSERT INTO backup_targets (name, type, hostname, path, capacity_tb, description) VALUES
  ('Veeam Backup Repository (NAS)', 'nas', 'nasbackup01.av-test.int', '/backup/veeam', 120, 'Primärer Veeam Repository auf NAS'),
  ('LTO-9 Tape Library', 'tape-lto9', 'tapeserver01.av-test.int', NULL, 1000, 'Quantum LTO-9 Tape Library, GFS-Policy'),
  ('Offsite rsync Server', 'offsite-rsync', 'offsite-backup.av-test.int', '/backup/offsite', 50, 'Externer Offsite-Server per rsync über VPN'),
  ('Lokaler Backup-Server', 'backup-server', 'b15na.av-test.int', '/var/backup', 20, 'Lokaler Backup-Server im Rack'),
  ('Proxmox Backup Server', 'backup-server', 'pbs01.av-test.int', '/mnt/datastore', 80, 'Proxmox Backup Server für VMs')
ON CONFLICT DO NOTHING;

INSERT INTO servers (name, hostname, type, os, role, notes) VALUES
  ('b15na', 'b15na.av-test.int', 'physical', 'Debian 12', 'PostgreSQL 17/18 + Zabbix DB', 'Aktuell pg_upgrade in Arbeit'),
  ('b20na', 'b20na.av-test.int', 'physical', 'Debian 12', 'Datenbankserver', NULL),
  ('server4', 'server4.av-test.int', 'physical', 'Debian 12', 'Applikationsserver', NULL),
  ('Proxmox-01', 'pve01.av-test.int', 'physical', 'Proxmox VE 8', 'Hypervisor', 'Cluster-Node 1'),
  ('Hyper-V-01', 'hv01.av-test.int', 'physical', 'Windows Server 2022', 'Hyper-V Hypervisor', NULL),
  ('FreeIPA-01', 'ipa01.av-test.int', 'vm-proxmox', 'Rocky Linux 9', 'FreeIPA Master', 'Docker-basiert'),
  ('Samba-FS', 'fs01.av-test.int', 'physical', 'Debian 12', 'Dateiserver / Samba', '360TB XFS RAID6'),
  ('Kubernetes-Master', 'k8s-master01.av-test.int', 'physical', 'Debian 12', 'K8s Control Plane', NULL),
  ('Graylog', 'graylog01.av-test.int', 'vm-proxmox', 'Debian 12', 'Log-Management', 'Graylog 7.0'),
  ('andynas', 'andynas.local', 'physical', 'Debian 12', 'Privater NAS / Homelab', NULL)
ON CONFLICT DO NOTHING;

INSERT INTO backup_methods (name, type, description) VALUES
  ('Veeam Agent Linux', 'veeam-agent', 'Veeam Agent for Linux – Image-Level Backup'),
  ('Veeam Agent Windows', 'veeam-agent', 'Veeam Agent for Windows – Image-Level Backup'),
  ('Veeam B&R VM-Backup', 'veeam-br', 'Veeam Backup & Replication – VM Snapshot Backup'),
  ('Proxmox Backup Server', 'veeam-br', 'PBS native VM/CT Backup via proxmox-backup-client'),
  ('pg_dump', 'bash-script', 'PostgreSQL Dump via pg_dump / pg_dumpall'),
  ('rsync', 'rsync', 'Rsync-basierte Datei-Sicherung (lokal oder remote)'),
  ('Bash-Script (tar+gpg)', 'bash-script', 'Eigenes Backup-Skript: tar, optional GPG-Verschlüsselung'),
  ('Zabbix Config Backup', 'bash-script', 'GitLab CI-basiertes Konfigurations-Backup'),
  ('Veeam Tape Job', 'veeam-br', 'Veeam Tape Job (GFS) – von Repository auf LTO-9'),
  ('rsync offsite', 'rsync', 'Rsync über VPN auf Offsite-Server')
ON CONFLICT DO NOTHING;

INSERT INTO backup_sources (server_id, name, type, path, description) VALUES
  (1, 'PostgreSQL 18 (Zabbix)', 'database', '/var/lib/postgresql/18', 'Zabbix-Datenbank mit TimescaleDB'),
  (1, 'Systemkonfiguration b15na', 'config', '/etc', 'Alle Konfigurationsdateien'),
  (2, 'PostgreSQL 18 (b20na)', 'database', '/var/lib/postgresql/18', 'Produktionsdatenbank'),
  (4, 'Alle VMs (Proxmox-01)', 'vm-full', '/etc/pve', 'Alle laufenden VMs via PBS'),
  (5, 'Alle VMs (Hyper-V-01)', 'vm-full', 'C:\\Hyper-V', 'Alle Hyper-V VMs'),
  (7, 'Samba Shares (360TB)', 'share', '/mnt/data', 'Produktions-Dateiserver, XFS RAID6'),
  (7, 'Samba Konfiguration', 'config', '/etc/samba', 'smb.conf + Freigaben-Konfiguration'),
  (6, 'FreeIPA LDAP Dump', 'database', '/var/lib/dirsrv', 'FreeIPA Verzeichnisdienst-Backup'),
  (8, 'Kubernetes etcd', 'kubernetes', '/var/lib/etcd', 'K8s Cluster State'),
  (8, 'K8s Persistent Volumes', 'kubernetes', '/mnt/k8s-pv', 'Persistente Volumes der Workloads'),
  (10, 'Home Assistant Config', 'config', '/config', 'HA-Konfiguration + Automationen'),
  (9, 'Graylog Index + Config', 'config', '/etc/graylog', 'Graylog-Konfiguration')
ON CONFLICT DO NOTHING;
