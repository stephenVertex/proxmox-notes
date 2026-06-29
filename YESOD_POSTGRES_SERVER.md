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
| **Disk** | 60GB (raw on local-lvm; resized from 30GB on 2026-06-29) |
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
- **Tailscale Hostname**: `yesod-postgres-server`
- **Hostname**: `yesod-postgres-server`
- **IP Assignment**: DHCP from LAN router
- **DNS**: Added to local `/etc/hosts` on admin machines

## Tailscale Access
- **Status**: ✅ Joined to tailnet `tailb4b58.ts.net`
- **URL**: `https://login.tailscale.com/admin/machines` (admin console)
- **CLI check**: `tailscale status` on any tailnet node shows `100.115.10.68 yesod-postgres-server ... linux -`

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
- **Size:** ~170 MB per backup (compressed; database is ~2.3 GB as of 2026-06-29)
- **Total estimated:** ~20 GB for a full 30-day window (30 daily × 170 MB)

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

### Off-VM Backup via NAS (Active)
**Status:** Active as of 2026-06-01
**Target:** Synology NAS (`homestar.local`, 192.168.0.123) — `proxmox-backups` share (WORM enabled)
**Mount:** `/mnt/proxmox-backups` on `seykhl` via CIFS

### NAS Share Details
- **Host:** `192.168.0.123` (Synology NAS)
- **Share:** `proxmox-backups`
- **User:** `proxmox-backup`
- **WORM:** Enabled (compliance mode) — files cannot be deleted or modified after writing

### Mount Configuration
```bash
# Mount command (also in /etc/fstab)
mount -t cifs //192.168.0.123/proxmox-backups /mnt/proxmox-backups \
  -o username=proxmox-backup,password=Pmxb2122!,vers=3.0,iocharset=utf8,_netdev
```

### fstab Entry
```
//192.168.0.123/proxmox-backups /mnt/proxmox-backups cifs username=proxmox-backup,password=Pmxb2122!,vers=3.0,iocharset=utf8,_netdev 0 0
```

### Host Backup Script
- **Script:** `/root/sync-yesod-backups.sh`
- **Schedule:** Every hour at `:05` via cron
- **Action:** Pulls daily (midnight) pg_dump backups from VM to NAS
- **Note:** Only syncs `*-0000.sql.gz` files. Hourly backups are NOT synced to NAS
  to avoid WORM accumulation. `--delete` removed because WORM prevents deletion.

```bash
#!/bin/bash
# Pull daily pg_dump backups from yesod-postgres-server to NAS share
# Only syncs midnight (00:00) backups to reduce WORM accumulation
# --delete removed: WORM compliance mode prevents file deletion
rsync -avz -e 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' \
  --include='*-0000.sql.gz' --exclude='*' \
  stephen@192.168.0.155:/var/backups/postgresql/ \
  /mnt/proxmox-backups/yesod-postgres-server/pg_dump/ 2>/dev/null
```

### Host Crontab Entries
```cron
5 * * * * /root/sync-yesod-backups.sh
0 2 1 * * vzdump 102 --dumpdir /mnt/proxmox-backups/yesod-postgres-server/vzdump/ --compress zstd --mode snapshot --remove 1 --maxfiles 2
```

### Backup Locations on NAS
| Type | Path | Retention |
|------|------|-----------|
| pg_dump | `/mnt/proxmox-backups/yesod-postgres-server/pg_dump/` | Daily midnight backups only (~170 MB each, accumulates on WORM) |
| vzdump | `/mnt/proxmox-backups/yesod-postgres-server/vzdump/` | Monthly snapshots (WORM prevents `--maxfiles` rotation) |

### WORM Limitation and Rotation Failure (Fixed 2026-06-29)
The NAS WORM compliance mode prevents all file deletion, which caused both rotation
mechanisms to silently fail:
- **rsync `--delete`** had no effect — 195 hourly backups accumulated over 7 days (23 GB)
- **vzdump `--maxfiles 2`** had no effect — 4 weekly snapshots accumulated (42 GB)

**Fix applied:**
1. rsync now only syncs daily midnight backups (`*-0000.sql.gz`), reducing growth from
   ~4 GB/day to ~170 MB/day. `--delete` flag removed.
2. vzdump changed from weekly to monthly (1st of month at 02:00), reducing accumulation
   to ~1 snapshot/month (~15-20 GB each).

**Note:** Old WORM-locked files on the NAS cannot be removed. They will remain until
the WORM retention period expires (check Synology DSM settings for the WORM quota/retention
configuration on the `proxmox-backups` share).

### Why WORM Matters
The NAS share is configured with **WORM (Write Once Read Many)** in compliance mode. This means:
- Once a file is written, it **cannot be deleted, modified, or renamed**
- Protection is enforced at the filesystem level, not just permissions
- Even if the Proxmox host is compromised, the attacker cannot destroy or encrypt your backups
- This is the gold standard for immutable backup storage

### Previous Failed Attempt
**Attempted:** 2026-05-31
**Disk:** `/dev/sda` (WDC WD5000LPLX-08ZNTT0, 500 GB)
**Issue:** Disk failed during first write test. SMART shows `FAILED` with 2,840 reallocated sectors.
**Action:** Disk unmounted, removed from `/etc/fstab`, and declared unusable.
**Resolution:** Switched to NAS-based off-VM backups instead of host disk.
