# Session Summary — 2026-05-31

## Objective
Audit and improve backup setup for `yesod-postgres-server` (VMID 102) on Proxmox host `seykhl`.

## What Was Done

### 1. Audited Existing Backups
- `pg_dump` script `/home/stephen/pg_backup.sh` is active
- Runs every hour via cron at `:00`
- ~8.7 MB per backup
- 52 files currently in `/var/backups/postgresql/` (~426 MB)

### 2. Updated Retention Policy
- **Old:** 48 hours of hourly backups
- **New:** Hourly for 5 days + daily (midnight) for 30 days
- Updated backup script and `YESOD_POSTGRES_SERVER.md` documentation
- Estimated total at steady state: ~1.5 GB

### 3. Attempted Off-VM Backup to Host Disk
- Discovered `/dev/sda` (WDC WD5000LPLX-08ZNTT0, 500 GB) on `seykhl` was unused
- Wiped old BitLocker partition, created GPT + ext4
- Mounted at `/mnt/backups`, created `yesod-postgres-server/pg_dump` and `yesod-postgres-server/vzdump` directories
- Set up SSH key from host to VM for passwordless rsync
- Set up hourly rsync cron job (`/root/sync-yesod-backups.sh`) at `:05` every hour
- Set up weekly vzdump snapshot cron job at 2:00 AM on Sundays
- rsync test worked: 52 files copied, 432 MB total
- **vzdump test failed** — disk went read-only during first write

### 4. Disk Failure Discovered
- `/dev/sda` remounted read-only due to I/O errors
- SMART shows `FAILED` status with 2,840 reallocated sectors
- **Action:** Unmounted disk, removed from `/etc/fstab`, declared unusable
- rsync cron and vzdump cron jobs remain configured on host but will fail until disk is replaced

### 5. Documentation Updated
- `YESOD_POSTGRES_SERVER.md` updated with:
  - New tiered backup script and retention
  - Notes on off-VM backup attempt and failure
  - Recommended future off-VM backup setup

### 6. Issue Tracking
- Created `PROXMOX-0iu`: Off-VM backup for yesod-postgres-server blocked by failing sda drive
- P2, open, ready to resume when healthy drive is available

### 7. GitHub Repo Created
- New repo: `https://github.com/stephenVertex/proxmox-notes`
- All project files pushed to `main`

## Current Backup Status

| Layer | Status | Details |
|-------|--------|---------|
| In-VM pg_dump | ✅ Active | Hourly, 5 days hourly + 30 days daily |
| Off-VM copy | ❌ Blocked | Failing disk — needs replacement |
| Full VM snapshot | ❌ Blocked | Failing disk — needs replacement |

## Recommended Next Steps
1. Replace failing `sda` with a healthy drive (NAS drive, USB external drive, or new disk)
2. Re-run the same setup: format, mount, re-enable rsync + vzdump cron jobs
3. The off-VM backup plan is fully documented in `YESOD_POSTGRES_SERVER.md`

## Notes
- `rsync` was installed on both `seykhl` host and `yesod-postgres-server` VM
- Host SSH key (`/root/.ssh/id_rsa.pub`) was added to VM `authorized_keys`
- `sda` is physically safe to leave installed — it's just unmounted and unused
- If you plug in a USB drive, it will appear as a different device (e.g., `/dev/sdb` or `/dev/sdc`) and won't conflict with `sda`
