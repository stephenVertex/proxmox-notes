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

**Traced live on 2026-09-05, approximately 13:15 Pacific. No backup job or
service was changed, no backup was triggered, and no restore was performed.**

The intended chain is hourly guest SQL dumps, an hourly Seykhl pull to the NAS,
and a weekly full VM archive. None currently establishes a recent production
backup after migration.

| Layer | Configuration | Observed result |
|---|---|---|
| Guest SQL dumps | `dolt` user cron at minute 0, every hour | Cron invokes the script; `/var/backups/dolt` is empty |
| NAS SQL copy | Seykhl root cron at minute 10, every hour | Still pulls the obsolete `.0.150`; NAS `dolt_dump` directory is empty |
| Weekly production VM archive | Seykhl Monday 02:00, VM 100 | August 31 failed with `VM is locked (migrate)`; targets the old VM |
| Current production VM 124 | Sefer scheduled VM backups | Not included in either configured job |
| Static seed VM 100 | Sefer daily 03:30 | Protects the August 27 seed, not ongoing production writes |

### Hourly guest dump script

The Dolt user's crontab is:

```cron
0 * * * * cd /home/doltdb/databases/doltsvr && bash dolt_backup.sh
```

`/home/doltdb/databases/doltsvr/dolt_backup.sh` enumerates child directories
containing `.dolt/config.json`; all 33 current repository directories match.
For each, it changes into the repository and invokes
`dolt dump -fn "${db_name}.sql" 2>/dev/null`. If that file exists, it gzips it
into `/var/backups/dolt/<database>-<YYYYMMDD-HHMM>.sql.gz` and removes the
intermediate SQL file. Finally, it deletes dumps matching `-mtime +5`.

The installed `dolt dump --help` describes a working-set table export. These
SQL files would not preserve the complete Dolt commit/branch history and are
not a replacement for a full repository or VM backup.

The immediate likely failure is command lookup: Dolt exists only at
`/usr/local/bin/dolt`, while the user crontab and script set no PATH. A
read-only reproduction as user `dolt` with `PATH=/usr/bin:/bin` cannot find
`dolt`. The PATH lines in system crontab files do not configure this separate
user crontab. The backup directory is owned by `dolt`, writable by that user,
and has 2.1 GiB filesystem space available, so those checks do not explain the
empty output. An actual dump was not executed during diagnosis; additional
failures may become visible once command lookup is corrected.

Failure reporting is also broken: dump stderr is discarded, command exit
status is not checked, and the script can finish with a success message even
when no database was dumped. The 11:00, 12:00 and 13:00 Pacific cron journal
entries confirm invocation and report `No MTA installed, discarding output`.
There is no retained per-run output from those invocations.

### NAS synchronization and retained archives

Seykhl `/root/sync-doltsvr-backups.sh` uses `rsync --delete` to pull:

```text
stephen@192.168.0.150:/var/backups/dolt/
  -> /mnt/proxmox-backups/doltsvr/dolt_dump/
```

It suppresses stderr and disables SSH host-key verification. The source IP is
obsolete; production is `192.168.20.150` / Tailscale `100.101.145.38`.
The NAS destination was confirmed empty through Sefer's working mount.
Changing the address alone will not fix the empty source or failure reporting.

The newest `.vma.zst` found in the production-specific NAS directory is:

```text
/mnt/proxmox-backups/doltsvr/vzdump/vzdump-qemu-100-2026_08_27-22_50_11.vma.zst
```

It is 18,303,329,616 bytes; its log reports `Finished Backup of VM 100` at
22:54:07 on August 27. This is the documented cold backup from before the
migration. The August 31 log reports a stopped VM followed by
`Backup of VM 100 failed - VM is locked (migrate)` and has no matching archive.
No VM124 archive was found in Sefer's standard NAS `dump` directory. These
checks establish files and log results, not present-day restorability or the
absence of every possible manual backup elsewhere.

Root's separate six-hour `/home/doltdb/cleanup_autobackups.sh` deletes temporary
`*beads-autobackup` directories under `/home/tmp`. It creates no backup and
must not be counted as a durable recovery layer.

Repair tracking: `proxmox-uev`; see [BACKUPS.md](BACKUPS.md). Before a production
upgrade, establish a fresh recoverable backup and rehearse restoring it.

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
