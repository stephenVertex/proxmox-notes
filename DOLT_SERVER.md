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

**Repaired 2026-09-05.** Production stays on Dolt 2.1.10. The hourly backup now
uses Dolt-native snapshots, and Sefer also schedules a full VM124 backup.

| Layer | Schedule (Pacific) | Destination |
|---|---|---|
| Native database backups | Hourly at :05; Sefer `dolt-nas-backup.timer` | `/mnt/proxmox-backups/doltsvr/native/` |
| Full VM124 archive | Daily 02:30; Proxmox `doltsvr-production` job | `/mnt/proxmox-backups/dump/vzdump-qemu-124-*.vma.zst` |
| Static seed VM100 | Existing daily 03:30 job | Separate historical seed; not current production protection |

### Native hourly backup

Sefer runs [backup-dolt-to-nas](scripts/backup-dolt-to-nas) through
[dolt-nas-backup.service](systemd/dolt-nas-backup.service) and its
[timer](systemd/dolt-nas-backup.timer). The host connects to
`192.168.20.150` using a dedicated SSH key at `/root/.ssh/dolt-nas-backup`.
The guest host key was obtained through authenticated Proxmox guest execution
and pinned in `/root/.ssh/dolt-nas-backup.known_hosts`.

The public key on VM124 is restricted to source `192.168.20.10`, with forwarding
and interactive access disabled, and a forced
[dolt-backup-export](scripts/dolt-backup-export) command. Only create, checksum,
read, acknowledge, and isolated verification operations are available. Private
keys and database credentials are not stored in this repository.

For each run:

1. Check NAS mount and capacity, then acquire exclusive host/guest locks.
2. Compare the filesystem database inventory with `SHOW DATABASES`. Include
   the parent `doltsvr` database as well as the 33 child databases.
3. As the `dolt` account, call `/usr/local/bin/dolt backup sync-url` for every
   database into a unique staging directory under `/home/dolt-backups`.
4. Include server YAML/unit settings, global Dolt configuration, `.doltcfg`,
   and each database's local configuration and repository-state files. Produce
   a JSON inventory and SHA-256 checksums for every payload file.
5. Pack the completed generation as `doltsvr-<UTC timestamp>.tar.gz`, transfer
   it to the NAS, check its SHA-256 against the guest, test gzip integrity,
   and publish the final name plus a `.sha256` sidecar.
6. Record `/var/lib/dolt-nas-backup/last-success` on Sefer, then acknowledge
   delivery and remove the guest archive. Retain failed transfers for retry.

Native snapshots preserve committed history, branches, tags and working sets.
They are taken sequentially per database, not as one cross-database transaction.
The whole-VM backup additionally captures the complete machine environment.
See the [official Dolt backup semantics](https://www.dolthub.com/docs/sql-reference/server/backups/).

The guest uses `/home` rather than the small `/var` filesystem. New generation
creation requires 10 GiB free there; host delivery requires 200 GiB free on the
NAS. The service has a 50-minute timeout. Errors reach the systemd journal and
fail the service, rather than being silently discarded by cron. This adds
observable failure state; no external alert destination was configured.

### Full VM backup and retention

The new `doltsvr-production` job targets **Sefer VM124**, in snapshot mode with
zstd compression and QEMU guest-agent freeze/thaw. It does not stop the Dolt
SQL service. A missed daily run is caught up by Proxmox.

Both new backup destinations currently retain every completed generation.
The VM job explicitly uses `remove=0` / `keep-all=1`; the native script does
not delete NAS archives. This avoids the existing NAS pruning failures without
claiming that a time-based retention policy is enforced. At approximately
2 GB per hourly native archive, native backups alone add roughly 48 GB/day;
allow for full VM archives too. Reconcile NAS retention and capacity under
`proxmox-cba`. Older archives and failed partial transfers are not silently
removed by these scripts.

### Verification and recovery

Use [verify-dolt-backup](scripts/verify-dolt-backup) to stream a NAS generation
back to a scratch directory, verify its payload checksums, restore every
native database, run `dolt fsck`, and open the restored working sets through
SQL. It never writes to the production data directory. Scratch data is removed
when verification exits; the report remains in VM124
`/home/dolt-backups/last-restore-report.json`.

From Sefer, run a backup or inspect status:

```bash
systemctl start dolt-nas-backup.service
systemctl status dolt-nas-backup.service --no-pager
journalctl -u dolt-nas-backup.service -n 60 --no-pager
systemctl list-timers dolt-nas-backup.timer --no-pager
cat /var/lib/dolt-nas-backup/last-success
pvesh get /cluster/backup/doltsvr-production --output-format json
```

To verify the latest NAS copy from Sefer (avoid overlapping a scheduled run):

```bash
filename=$(awk '{print $3}' /var/lib/dolt-nas-backup/last-success)
ssh -i /root/.ssh/dolt-nas-backup -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/root/.ssh/dolt-nas-backup.known_hosts \
  root@192.168.20.150 verify \
  < "/mnt/proxmox-backups/doltsvr/native/$filename" \
  > /var/lib/dolt-nas-backup/restore-report.json
```

For actual recovery, restore to a new isolated directory or VM first. Use
`dolt backup restore file:///.../native/<database> <new-directory>` for native
repositories. Review the accompanying configuration before restoring it, and
use the full VM archive when the OS, service identities and complete server
state are required. Never restore over the active primary.

### September 5 backup evidence

The new native generation is:

```text
/mnt/proxmox-backups/doltsvr/native/doltsvr-20260905T210440Z.tar.gz
```

The earlier `20260905T205942Z` generation was a 33-child-database test and is
marked with an `.INCOMPLETE.txt` sidecar on the NAS; do not use it for full
recovery.

The `20260905T210440Z` generation contains all 34 databases and accompanying
configuration, is 2,000,476,733
bytes, and was delivered successfully at 14:07:07 Pacific. Its SHA-256 is:

```text
6422e890b1643381772f646411c230aff8436a6dc28169cffe90451592a07511
```

At 14:14:08 Pacific, the NAS archive was streamed back and all **34 databases
restored successfully into scratch space** using Dolt 2.1.10. Every repository
passed `dolt fsck` and a SQL table-inventory query; all **219 payload files**
passed SHA-256 verification. The scratch restore was then removed. The report
is retained on Sefer at `/var/lib/dolt-nas-backup/restore-report-20260905.json`
and beside the NAS archives as `restore-report-20260905T210440Z.json`.
The restricted SSH endpoint also rejected an attempted path outside the
archive spool. Production Dolt remained active throughout.

The full VM backup completed at 14:03:41 Pacific, with a successful
`zstd -t` integrity check afterward:

```text
/mnt/proxmox-backups/dump/vzdump-qemu-124-2026_09_05-14_00_12.vma.zst
```

It is 18,762,035,393 bytes. QEMU guest-agent freeze/thaw was recorded in the
backup log. This archive has not been boot-restored as a VM during this repair;
the separate native restore exercise validates the database recovery path.
The VM snapshot preceded the final backup-script revisions and cron retirement;
if restoring that particular VM archive, reapply the current backup scripts
and retired-cron changes from this runbook before returning it to service.

### Retired broken workflow

The old Dolt-user hourly SQL-dump cron entry was removed. It called bare
`dolt` outside the default cron PATH, suppressed errors, discarded output via
cron's missing MTA, and skipped the parent database. Both its local dump
directory and the NAS SQL-dump destination were empty.

Seykhl's obsolete hourly Dolt rsync and Monday VM100 backup cron entries were
removed. Its old sync script now exits with a retirement notice instead of
pulling `.0.150` with `--delete`. Original crontabs and the old sync script are
saved under `/root/dolt-backup-repair-20260905` on the relevant machines.
The unrelated PostgreSQL/DocuSeal cron entries were preserved. Root's six-hour
cleanup of temporary Beads autobackups was also preserved; it is not a durable
backup layer.

Before repair, the newest production-specific NAS archive found was the
August 27 cold backup. The August 31 attempt failed with `VM is locked
(migrate)`. Current verification evidence below supersedes that coverage gap.

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
