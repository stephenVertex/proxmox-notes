# Dolt production server

**Last verified:** 2026-09-05 from Sefer VM 124 and its running guest.

## Current deployment

Production `doltsvr` has moved from Seykhl VM 100 to **Sefer VM 124**. This
is the existing Dolt 2.1.10 write primary, moved as a VM; it is not the
Dolt 2.3.1 static seed on Sefer VM 100. The Seykhl copy is stopped and still
has autostart enabled. Do not start the old copy alongside production.

| Setting | Current value |
|---|---|
| Host | Sefer, VLAN `192.168.20.10`; direct 10 GbE `192.168.0.100` |
| VMID / name | 124 / `doltsvr` |
| Guest OS | Debian 13 (Trixie), as reported by `/etc/os-release` |
| CPU / memory | 4 host vCPU / 24 GiB fixed RAM |
| Disk | 64 GiB raw file `local:124/vm-124-disk-0.raw` on mirrored `rpool` |
| Bridge / MAC | `vmbr1` / `BC:24:11:D0:43:5D` |
| VLAN IPv4 | `192.168.20.150` (old `192.168.0.150` is obsolete) |
| Tailscale IPv4 | `100.101.145.38` |
| Boot policy | `onboot=1`; QEMU guest agent responds |
| Dolt | 2.1.10 |
| Service | `dolt-sql-server.service`, enabled and active |
| Service user / working directory | `dolt` / `/home/doltdb/databases/doltsvr` |
| Listener | TCP 3306, wildcard listener observed |

The administrator Mac's `doltsvr` SSH alias still pointed to the old LAN IP
when inspected. Use the VLAN or Tailscale address and verify the guest's host
key before updating client aliases. See [NETWORK.md](NETWORK.md).

## Data and access

The active unit is `/etc/systemd/system/dolt-sql-server.service`. It runs in
`/home/doltdb/databases/doltsvr`. The historical moves of `/var/lib/doltdb`
and `/var/tmp` into `/home` are explained in the incident record below.
No repository integrity scan, data mutation, service restart or upgrade was
performed during this audit. A listening service does not prove every database
or client is healthy.

```bash
ssh -o BatchMode=yes stephen@192.168.20.150 'dolt version; systemctl is-active dolt-sql-server'
ssh -o BatchMode=yes root@sefer 'qm status 124; qm guest cmd 124 network-get-interfaces'
ssh -o BatchMode=yes root@sefer 'qm guest exec 124 -- ss -lntp'
```

The guest's `stephen` login does not have unrestricted passwordless sudo;
use authenticated Proxmox guest execution for privileged read-only inspection.
Credentials remain in protected server/client configuration, not this document.

## Static seed and replication

Sefer VM 100 (`doltsvr-sefer`, `192.168.0.160`) still runs no SQL server,
has no `/etc/dolt/config.yaml`, and retains Dolt 2.3.1. It is a static
August 27 seed, not a live replica. VMs 122 and 123 remain protected, stopped
and without NICs as offline rehearsal/seed sources.

[DOLT_STANDBY.md](DOLT_STANDBY.md) retains the seed validation evidence.
[DOLT_LIVE_REPLICA_PLAN.md](DOLT_LIVE_REPLICA_PLAN.md) is a historical plan
requiring redesign: the two live Dolt guests now share Sefer. A replica there
would not protect against losing that physical host.

## Backups

The Dolt user's current crontab still runs hourly:

```cron
0 * * * * cd /home/doltdb/databases/doltsvr && bash dolt_backup.sh
```

Root also schedules `/home/doltdb/cleanup_autobackups.sh` every six hours.
The audit's read-only listing found no dump files under `/var/backups/dolt`;
scheduling alone does not prove usable dumps. The SQL-dump script and its
output location/success need revalidation before relying on this layer.

Seykhl's `/root/sync-doltsvr-backups.sh` still reads the obsolete
`192.168.0.150:/var/backups/dolt/`. Its weekly `vzdump 100` targets the stopped
Seykhl copy. **Sefer VM 124 is not in either scheduled Sefer backup job.**
The nightly Sefer backup of VM 100 protects the static seed, not production.
See [BACKUPS.md](BACKUPS.md), follow-up `proxmox-uev`.

The historic NAS recovery directory is
`/mnt/proxmox-backups/doltsvr/vzdump/`. Restore archives into an unused,
isolated VMID with networking disabled; verify date, source VM identity and
contents before any cutover. Do not restore onto live VM 124 or blindly use
old VMID 100 instructions.

## Historical upgrades and incidents

The following dated records describe the pre-migration service. Their version,
size and database-count observations are historical, not current acceptance
results. Any rollback requires a new maintenance plan and current backup.

## Upgrade History

### 2.0.3 → 2.1.0 (2026-06-01)
- **Reason**: Critical bug fix for TEXT/BLOB column encoding during ALTER TABLE
- **Backup**: Old binary saved at `/usr/local/bin/dolt-2.0.3-backup`
- **Downtime**: ~10 seconds (service stop + replace + start)
- **Verification**: Service started successfully, SQL queries responsive
- **Rollback**: `sudo cp /usr/local/bin/dolt-2.0.3-backup /usr/local/bin/dolt && sudo systemctl restart dolt-sql-server`

### 2.1.0 → 2.1.10 (2026-06-26)
- **Reason**: Routine upgrade (2.1.0 → 2.1.9 → 2.1.10); 9 patch releases with bug fixes
- **Backup**: Old binary saved at `/usr/local/bin/dolt-2.1.0-backup`
- **Downtime**: ~2 minutes (service stop + download + install + start)
- **Verification**: All 25 databases visible, `yesod_aicoe` has 12,055 issues, service healthy at 453MB
- **Rollback**: `sudo cp /usr/local/bin/dolt-2.1.0-backup /usr/local/bin/dolt && sudo systemctl restart dolt-sql-server`

## Incident: Disk Full Crash (2026-06-25)

- **Cause**: `/var` partition (2.9GB) filled to 100%. Dolt panicked with
  `no space left on device` while committing to `yesod_aicoe` database.
  Systemd restarted 5 times in rapid succession, all failed for same reason,
  then gave up.
- **Contributing factors**: `/var/tmp/` had ~1.1GB of beads autobackup dirs
  from Dolt clients; `/var` partition was only 2.9GB while `/home` had 47GB.
- **Fix**: Moved `/var/lib/doltdb/` to `/home/doltdb/` (44GB free), created
  symlink at `/var/lib/doltdb -> /home/doltdb`, updated systemd service
  `WorkingDirectory`, backup script `DATA_DIR`, and crontab to reference
  `/home/doltdb` directly. Cleaned `/var/tmp` autobackups and apt cache.
- **Downtime**: ~12 minutes (17:26 PDT crash to 17:38 PDT recovery)
- **Data loss**: None — all 19 databases verified intact

## Incident: /var/tmp Filled Again (2026-06-26)

- **Cause**: Beads autobackup feature wrote 2.2GB to `/var/tmp/` (on the 2.9GB
  `/var` partition), filling it to 100% again. The Dolt service was technically
  running but completely blocked — memory ballooned to 10GB, CPU pinned at 171%,
  all queries failing with `no space left on device`.
- **Fix**: Stopped service, relocated `/var/tmp` to `/home/tmp` via symlink
  (`/var/tmp -> /home/tmp`, 42GB free), cleaned stale autobackups, restarted.
- **Downtime**: ~2 minutes
- **Data loss**: None — `yesod_aicoe` had 11,735 issues verified after restart
