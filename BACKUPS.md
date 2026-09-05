# Backup configuration and live verification

**Verified:** 2026-09-05. Sources: Sefer `/etc/pve/jobs.cfg`, both root
crontabs, systemd timer/results, guest backup file metadata and Proxmox task logs.

## Sefer scheduled VM backups

All three jobs use snapshot mode, zstd and `nas-backups` at
`/mnt/proxmox-backups`. Host timezone is America/Los_Angeles.

| Job | Schedule | VMIDs | Configured retention |
|---|---|---|---|
| `doltsvr-production` | Daily 02:30 | 124 only | Keep all; NAS retention pending |
| `sefer-light-services` | Daily 03:30 | 100,103,105,107,113,114,116,117,118,119,120 | 7 daily / 4 weekly / 3 monthly |
| `yesod-semantic-graph` | Daily 04:30 | 121 only | 7 daily / 4 weekly / 3 monthly |

**September 5 result for the original two jobs: both ended with `job errors`.** The logs show
completed archive transfers followed by failure to delete older NAS archives:
`Operation not supported`. For VM 121, 64 GiB transferred in 57 seconds and
the archive was 1.08 GB; pruning the August 29 archive then failed. GitLab VM
119 likewise transferred 380 GiB and wrote a 7.02 GB archive before pruning
failed. These observations do not prove archive restorability.

Task references on Sefer:

```text
UPID:sefer:002A3E3B:0474F312:6A9BEF2D:vzdump::root@pam:
UPID:sefer:002BA308:047A71E8:6A9BFD3F:vzdump:121:root@pam:
```

The deletion failure is consistent with the previously documented NAS WORM
restriction. NAS retention policy was not inspected in DSM. Reconcile the NAS
policy and Proxmox pruning configuration before claiming that retention works.

Pruning follow-up: `proxmox-cba`. The new VM124 backup completed successfully
at 14:03:41 Pacific and passed `zstd -t`; its job retains all archives.

## Coverage gaps after migration

Sefer's current scheduled jobs omit production PostgreSQL 102, Dertog 104,
LiteLLM 101, sb-edge 111 and the expanded runner/gate fleet.
Production Dolt 124 was added in the September 5 repair to its own daily job.
VM 100 in `sefer-light-services` is the isolated static Dolt seed, not the
production write primary. All 19 running test/experiment PostgreSQL containers
are on disposable `scratch` storage and have no scheduled Proxmox backup here.

Seykhl has no `/etc/pve/jobs.cfg` and no `nas-backups` Proxmox storage entry.
Its current and retired root cron entries are:

| Schedule | Existing command | Audit implication |
|---|---|---|
| Hourly :05 | `/root/sync-yesod-backups.sh` | Still reads `192.168.0.155`, now obsolete |
| Monthly day 1, 02:00 | `vzdump 102 ...` | Targets the stopped Seykhl copy, not Sefer VM 102 |
| Retired September 5 | `/root/sync-doltsvr-backups.sh` | Replaced by Sefer native Dolt backup timer |
| Retired September 5 | Monday `vzdump 100 ...` | Replaced by Sefer VM124 daily backup |
| Hourly :10 | `/root/sync-docuseal-backups.sh` | Still targets `.139`; successful recent transfer not established |

`findmnt` still lists the CIFS NAS mount on Seykhl, but that alone does not
prove reachability, successful synchronization, or coverage of the migrated
disks. Sefer has no root crontab. The Dolt repair subsequently removed the two
obsolete Dolt cron entries and added Sefer protection; other services remain
outstanding.
Coverage follow-up: `proxmox-uev`.

## Application backups

| Service | Current evidence | Limit |
|---|---|---|
| GitLab | `gitlab-app-backup.timer` at 01:30 Pacific; success, exit 0, finished 2026-09-05 01:31 | Restore rehearsal not repeated |
| Semantic graph pipeline PostgreSQL | `yesod-semantic-graph-backup.timer` at 04:15 Pacific; success, exit 0; September 5 custom dump is 6,218,546 bytes | Separate from failed VM pruning |
| Production PostgreSQL | Guest cron runs `/home/stephen/pg_backup.sh` hourly; 17:00 UTC September 5 dump files and globals exist | Stale host sync does not establish an off-VM copy |
| Dolt | Hourly native backup on Sefer at :05, plus daily VM124 snapshot at 02:30 | 34 databases restored, fsck/SQL checks passed, 219 payload checksums verified September 5; append-only retention pending NAS policy; [runbook](DOLT_SERVER.md#backups) |

A timestamp and nonzero file size are not a restore test. Earlier dated restore
proofs remain historical evidence in the relevant service document.

## Read-only checks

```bash
ssh -o BatchMode=yes root@sefer 'cat /etc/pve/jobs.cfg'
ssh -o BatchMode=yes root@sefer 'pvesh get /nodes/sefer/tasks --typefilter vzdump --limit 5 --output-format json'
ssh -o BatchMode=yes root@sefer 'systemctl show gitlab-app-backup.service -p Result -p ExecMainStatus -p InactiveEnterTimestamp'
ssh -o BatchMode=yes root@seykhl 'crontab -l'
```

Inspect the task log for an individual failed VM before rerunning anything;
the job status can reflect pruning failure after a successful transfer.
