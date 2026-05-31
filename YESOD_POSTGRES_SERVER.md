# Yesod Postgres Server - Build Plan

## Overview
Create `yesod-postgres-server` on Proxmox host `seykhl` as a Debian 13 VM running latest stable PostgreSQL.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 102 |
| **Name** | yesod-postgres-server |
| **OS** | Debian 13 "Trixie" (latest stable) |
| **CPU** | host (AVX passthrough required for modern tools) |
| **Cores** | 2 |
| **Memory** | 6GB |
| **Disk** | 30GB (raw on local-lvm) |
| **Network** | vmbr0 (bridge to LAN) |
| **Net Model** | virtio |
| **Display** | none (headless server) |

## Build Steps

### 1. Download Debian 13 Cloud Image (if not present)
```bash
# On seykhl (Proxmox host)
ssh root@seykhl

cd /var/lib/vz/template/iso/
# Download Debian 13 generic cloud image
wget https://cdimage.debian.org/images/cloud/trixie/latest/debian-13-generic-amd64.qcow2
```

### 2. Create VM on Proxmox
```bash
# Create empty VM
qm create 102 \
  --name yesod-postgres-server \
  --memory 6144 \
  --cores 2 \
  --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-single \
  --boot order=scsi0 \
  --ostype l26 \
  --agent enabled=1

# Import Debian 13 disk
qm disk import 102 /var/lib/vz/template/iso/debian-13-generic-amd64.qcow2 local-lvm

# Attach disk to VM
qm set 102 --scsi0 local-lvm:vm-102-disk-0

# Resize disk to 30GB
qm disk resize 102 scsi0 30G
```

### 3. Configure Cloud-Init
```bash
# Create cloud-init drive
qm set 102 --ide2 local-lvm:cloudinit

# Configure cloud-init user data (NO SSH key injection - user will handle manually)
qm set 102 --ciuser stephen
qm set 102 --cipassword lj*123NM

# Set IP (DHCP)
qm set 102 --ipconfig0 ip=dhcp
```

### 4. Start VM and PAUSE
```bash
qm start 102
```

**STOP HERE.** Wait for user to:
1. Confirm VM is fully booted
2. Add VM IP to local `/etc/hosts` as `yesod-postgres-server`
3. Set up passwordless SSH for this agent

**DO NOT PROCEED until user confirms.**

### 5. Post-Install Setup

#### 5.1 Update System
```bash
ssh stephen@<IP>
sudo apt update
sudo apt upgrade -y
```

#### 5.2 Install PostgreSQL
```bash
# Install latest stable PostgreSQL from Debian repos
sudo apt install -y postgresql postgresql-contrib

# Enable and start service
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Verify
sudo systemctl status postgresql
psql --version
```

#### 5.3 Configure PostgreSQL
```bash
# Switch to postgres user for initial setup
sudo -u postgres psql

# Create database and user for applications
CREATE USER stephen WITH PASSWORD 'lj*123NM' CREATEDB;
CREATE DATABASE stephen OWNER stephen;
\q

# Configure pg_hba.conf for local connections
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Ensure: local all all trust (for local unix socket connections)

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 5.4 Harden SSH
```bash
# Edit /etc/ssh/sshd_config
sudo nano /etc/ssh/sshd_config

# Set:
PermitRootLogin no
PasswordAuthentication yes  # (keep yes for now, can switch to key-only later)
PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart sshd
```

### 6. Verification Checklist
- [x] VM boots successfully
- [x] User `stephen` can login via SSH with password `lj*123NM`
- [x] `sudo` works for stephen
- [x] PostgreSQL service is running (PostgreSQL 17.10)
- [x] `psql` connects as stephen
- [x] Database `stephen` exists
- [x] VM responds to ping from LAN
- [x] Proxmox agent reports IP address

## Network Details
- **MAC Address**: BC:24:11:00:88:F5
- **LAN IP**: 192.168.0.155 (DHCP)
- **Tailscale IP**: 100.115.10.68
- **Hostname**: `yesod-postgres-server`
- **IP Assignment**: DHCP from LAN router
- **DNS**: Will be added to local `/etc/hosts` on admin machines

## PostgreSQL Connection

### Listen Addresses
```ini
listen_addresses = '100.115.10.68, 192.168.0.155, localhost'
```

### Access Rules (pg_hba.conf)
```ini
# Local socket
local   all             all                                     peer

# Localhost TCP
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

# LAN access
host    all             all             192.168.0.0/24          scram-sha-256

# Tailscale access
host    all             all             100.64.0.0/10           scram-sha-256
host    all             all             100.115.10.68/32        scram-sha-256
```

### Connection Parameters for Clients
| Parameter | Value |
|-----------|-------|
| **Host** | `yesod-postgres-server` (MagicDNS) or `100.115.10.68` or `192.168.0.155` |
| **Port** | `5432` |
| **Database** | `stephen` |
| **Username** | `stephen` |
| **Password** | `lj*123NM` |
| **SSL** | `disable` (Tailscale encrypts the tunnel) |

### psql
```bash
psql -U stephen -d stephen -h yesod-postgres-server
```

### Connection Strings
**Python:**
```python
DATABASE_URL = "postgresql://stephen:lj*123NM@yesod-postgres-server:5432/stephen"
```

**Node.js:**
```javascript
{ host: 'yesod-postgres-server', port: 5432, database: 'stephen', user: 'stephen', password: 'lj*123NM' }
```

**Go:**
```go
"host=yesod-postgres-server port=5432 user=stephen password=lj*123NM dbname=stephen sslmode=disable"
```

## Resources
- Proxmox Host: `seykhl` (192.168.0.202)
- Cloud Image: `/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2`
- VM Disk: `local-lvm:vm-102-disk-0`

## Notes
- CPU type `host` is critical — previous `jeffrey-dev` build failed with `kvm64` due to missing AVX instructions required by modern runtimes
- Debian 13 is current stable as of May 2026
- PostgreSQL version from Debian 13 repos is 17.10 (not 15.x as originally estimated)
- Keep cloud-init SSH key injection — if it fails, mount disk from host and manually inject

## Backup Configuration

### Tiered pg_dump Backup (Inside VM)
- **Script:** `/home/stephen/pg_backup.sh`
- **Schedule:** Every hour at `:00` via cron
- **Location:** `/var/backups/postgresql/stephen-YYYYMMDD-HHMM.sql.gz`
- **Retention:**
  - **Hourly:** kept for the last 5 days (120 backups)
  - **Daily:** midnight backups kept for the last 30 days
- **Size:** ~8.7 MB per backup (compressed)
- **Total estimated:** ~1.5 GB for a full 30-day window

### Backup Script Contents
```bash
#!/bin/bash
# PostgreSQL tiered backup
# - Hourly backups for the last 5 days
# - Daily (midnight) backups for the last 30 days

BACKUP_DIR="/var/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d-%H%M)
BACKUP_FILE="$BACKUP_DIR/stephen-${TIMESTAMP}.sql.gz"

# Create backup
pg_dump -U stephen stephen | gzip > "$BACKUP_FILE" 2>/dev/null

# Delete any backup older than 5 days that is NOT a midnight (00:00) backup
# This keeps hourly backups for the last 5 days
find "$BACKUP_DIR" -name "stephen-*.sql.gz" -mtime +5 ! -name "*-0000.sql.gz" -delete

# Delete any backup older than 30 days (keeps daily backups for 30 days)
find "$BACKUP_DIR" -name "stephen-*.sql.gz" -mtime +30 -delete
```

### Crontab Entry
```cron
0 * * * * /home/stephen/pg_backup.sh
```

### Restore Command
```bash
zcat /var/backups/postgresql/stephen-20260518-1703.sql.gz | psql -U stephen -d stephen
```

### Off-VM Backup Attempt (Status: BLOCKED)
**Attempted:** 2026-05-31
**Goal:** Mirror pg_dump backups and vzdump snapshots to a second physical disk on `seykhl`.
**Disk:** `/dev/sda` (WDC WD5000LPLX-08ZNTT0, 500 GB)
**Issue:** Disk failed during first write test. SMART shows `FAILED` with 2,840 reallocated sectors.
**Action:** Disk unmounted, removed from `/etc/fstab`, and declared unusable.
**Next Step:** Replace failing disk with a healthy drive before attempting off-VM backups again.

### Recommended Future Off-VM Backup Setup
Once a healthy secondary disk is installed:
1. **pg_dump mirror:** Hourly rsync from VM to host disk
2. **vzdump snapshots:** Weekly full-VM snapshot to host disk
3. **Retention:** Keep 2 vzdump snapshots on the host disk
