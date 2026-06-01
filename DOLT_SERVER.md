# Dolt Server - Backup Configuration

## Overview
`dolt-server` (VMID 100) is an Ubuntu VM on Proxmox host `seykhl` running the Dolt SQL server. This document covers the backup setup and configuration.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 100 |
| **Name** | dolt-server |
| **OS** | Ubuntu (latest stable) |
| **CPU** | host (AVX passthrough) |
| **Cores** | 2 |
| **Memory** | 24GB |
| **Disk** | 64GB (raw on local-lvm) |
| **Network** | vmbr0 (bridge to LAN) |
| **Net Model** | virtio |
| **Display** | none (headless server) |

## Network Details
- **MAC Address**: BC:24:11:D0:43:5D
- **LAN IP**: 192.168.0.150 (DHCP)
- **Hostname**: `doltsvr`
- **DNS**: Added to local `/etc/hosts` on admin machines

## Dolt Server Configuration
- **Service**: `dolt-server` (systemd)
- **User**: `dolt` (uid=999)
- **Working Directory**: `/var/lib/doltdb/databases/doltsvr`
- **Port**: 3306 (MySQL-compatible)
- **Version**: 2.1.0 (upgraded from 2.0.3 on 2026-06-01)

## Databases
The following databases are stored in `/var/lib/doltdb/databases/doltsvr/`:
- `beads_als`
- `beads_amplifier`
- `beads_aysp`
- `beads_chunkpdf`
- `beads_clip_together`
- `beads_hnalg`
- `beads_mvr`
- `beads_nbgen`
- `beads_opensymphony`
- `beads_ppg_pdf`
- `beads_scr_rename`
- `beads_scr_wrap`
- `beads_shup`
- `beads_sjbgtd`
- `beads_submgk`
- `beads_substack_sjbg_bridge`
- `beads_synapse`
- `beads_thmb`
- `yesod_aicoe`

## Backup Configuration

### Tier 1: In-VM Dolt Dumps (Hourly)
- **Script**: `/var/lib/doltdb/databases/doltsvr/dolt_backup.sh`
- **Schedule**: Every hour at `:00` via cron (dolt user)
- **Location**: `/var/backups/dolt/`
- **Format**: SQL dumps compressed with gzip
- **Retention**: 5 days (auto-deletes older)

### Backup Script Contents
```bash
#!/bin/bash
# Dolt database backup script
# Dumps all databases in /var/lib/doltdb/databases/doltsvr/ to SQL files

BACKUP_DIR="/var/backups/dolt"
DATA_DIR="/var/lib/doltdb/databases/doltsvr"
TIMESTAMP=$(date +%Y%m%d-%H%M)

mkdir -p "$BACKUP_DIR"

# Loop through each database directory and dump it
for db_dir in "$DATA_DIR"/*; do
    if [ -d "$db_dir" ] && [ -f "$db_dir/.dolt/config.json" ]; then
        db_name=$(basename "$db_dir")
        backup_file="$BACKUP_DIR/${db_name}-${TIMESTAMP}.sql.gz"
        
        echo "Backing up $db_name..."
        
        # Run dolt dump in the database directory
        cd "$db_dir"
        dolt dump -fn "${db_name}.sql" 2>/dev/null
        
        if [ -f "${db_name}.sql" ]; then
            # Compress and move to backup directory
            gzip -c "${db_name}.sql" > "$backup_file"
            rm "${db_name}.sql"
            echo "  -> $backup_file ($(du -h "$backup_file" | cut -f1))"
        else
            echo "  -> FAILED for $db_name"
        fi
    fi
done

# Delete backups older than 5 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +5 -delete

echo "Backup complete. Total backups: $(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l)"
```

### Crontab Entry (dolt user)
```cron
0 * * * * cd /var/lib/doltdb/databases/doltsvr && bash dolt_backup.sh
```

### Tier 2: NAS Mirror (Hourly)
- **Script**: `/root/sync-doltsvr-backups.sh` (on Proxmox host)
- **Schedule**: Every hour at `:10` via cron
- **Target**: Synology NAS (`homestar.local`, 192.168.0.123)
- **Path**: `/mnt/proxmox-backups/doltsvr/dolt_dump/`

### NAS Sync Script Contents
```bash
#!/bin/bash
# Pull dolt backups from doltsvr to NAS share
rsync -avz --delete -e 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' \
  stephen@192.168.0.150:/var/backups/dolt/ \
  /mnt/proxmox-backups/doltsvr/dolt_dump/ 2>/dev/null
```

### Tier 3: VM Snapshots (Weekly)
- **Schedule**: Every Monday at 2:00 AM
- **Target**: Synology NAS
- **Path**: `/mnt/proxmox-backups/doltsvr/vzdump/`
- **Retention**: 2 snapshots (auto-removes older)

### Crontab Entry (root on Proxmox host)
```cron
0 2 * * 1 vzdump 100 --dumpdir /mnt/proxmox-backups/doltsvr/vzdump/ --compress zstd --mode snapshot --remove 1 --maxfiles 2
```

## NAS Configuration
- **Host**: `192.168.0.123` (Synology NAS)
- **Share**: `proxmox-backups`
- **User**: `proxmox-backup`
- **WORM**: Enabled (compliance mode) — files cannot be deleted or modified after writing

### Mount Configuration
```bash
# Mount command (also in /etc/fstab on seykhl)
mount -t cifs //192.168.0.123/proxmox-backups /mnt/proxmox-backups \
  -o username=proxmox-backup,password=Pmxb2122!,vers=3.0,iocharset=utf8,_netdev
```

### fstab Entry
```
//192.168.0.123/proxmox-backups /mnt/proxmox-backups cifs username=proxmox-backup,password=Pmxb2122!,vers=3.0,iocharset=utf8,_netdev 0 0
```

## Backup Locations Summary

| Tier | Type | Location | Retention | Size |
|------|------|----------|-----------|------|
| 1 | In-VM dolt dumps | `/var/backups/dolt/` (VM) | 5 days | ~468 KB |
| 2 | NAS dolt dumps | `/mnt/proxmox-backups/doltsvr/dolt_dump/` | Mirrors VM | ~468 KB |
| 3 | NAS VM snapshots | `/mnt/proxmox-backups/doltsvr/vzdump/` | 2 snapshots | ~2.5 GB each |

## Restore Procedures

### Restore a Single Database from SQL Dump
```bash
# On doltsvr
zcat /var/backups/dolt/yesod_aicoe-20260601-1200.sql.gz | dolt sql
```

### Restore from VM Snapshot
```bash
# On Proxmox host (seykhl)
qmrestore /mnt/proxmox-backups/doltsvr/vzdump/vzdump-qemu-100-YYYY_MM_DD-HH_MM_SS.vma.zst 100
```

## Troubleshooting

### Check Backup Status
```bash
# On doltsvr
ls -la /var/backups/dolt/

# On Proxmox host
ls -la /mnt/proxmox-backups/doltsvr/
```

### Check Cron Jobs
```bash
# On doltsvr (as dolt user)
crontab -l

# On Proxmox host
crontab -l
```

### Manual Backup Test
```bash
# On doltsvr (as dolt user)
cd /var/lib/doltdb/databases/doltsvr
bash dolt_backup.sh

# On Proxmox host
bash /root/sync-doltsvr-backups.sh
```

## Resources
- Proxmox Host: `seykhl` (192.168.0.202)
- VM Disk: `local-lvm:vm-100-disk-0`
- Dolt Version: 2.1.0
- Dolt Documentation: https://docs.dolthub.com/

## Notes
- CPU type `host` is critical for modern tool compatibility
- Dolt SQL server runs as user `dolt` with working directory at `/var/lib/doltdb/databases/doltsvr`
- The `dolt_backup.sh` script must be run as the `dolt` user to access database files
- `rsync` was installed on both the VM and host for backup synchronization
- WORM protection on the NAS ensures backups are immutable once written

## Upgrade History

### 2.0.3 → 2.1.0 (2026-06-01)
- **Reason**: Critical bug fix for TEXT/BLOB column encoding during ALTER TABLE
- **Backup**: Old binary saved at `/usr/local/bin/dolt-2.0.3-backup`
- **Downtime**: ~10 seconds (service stop + replace + start)
- **Verification**: Service started successfully, SQL queries responsive
- **Rollback**: `sudo cp /usr/local/bin/dolt-2.0.3-backup /usr/local/bin/dolt && sudo systemctl restart dolt-sql-server`
