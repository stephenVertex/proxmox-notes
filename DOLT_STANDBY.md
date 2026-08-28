# Dolt standby on Sefer

**Last verified:** 2026-08-27

## Safety boundary

The production `doltsvr` at `192.168.0.150` remains the only write primary.
An authorized pause on 2026-08-27 was used to take a cold backup and fresh
seed; the production service was then restarted unchanged. Its Dolt version,
configuration, data directory, hostname, and client routing must not be changed
outside another explicit maintenance window.

VM 100 on `sefer` is an isolated migration target. It must remain under the
temporary guest hostname `doltsvr-sefer` until a controlled cutover. Do not
assign it the production `doltsvr` DNS, mDNS, or Tailscale identity early.

## VM inventory

| Setting | Value |
|---|---|
| Proxmox host | `sefer` (`192.168.0.100`) |
| VMID / name | 100 / `doltsvr-sefer` |
| OS | Debian 13 (Trixie) cloud image |
| CPU / memory | 4 host-type vCPU / 24 GiB fixed RAM |
| Disk | 100 GiB on mirrored `vmdata` ZFS |
| Network | `vmbr0`, virtio |
| MAC / LAN IP | `BC:24:11:69:D9:AB` / `192.168.0.160` |
| Addressing | Static cloud-init address; router reservation confirmed |
| mDNS | `doltsvr-sefer.local` via Avahi |
| Administration | `ssh stephen@192.168.0.160` |
| Dolt | 2.3.1, pinned from the official GitHub release |
| Data directory | `/home/doltdb/databases/doltsvr` owned by `dolt:dolt` |
| Service unit | `dolt-sql-server.service`, installed but disabled |
| VM backup | `sefer-light-services`, daily 03:30 to `nas-backups` |

The VM starts with Sefer, has Proxmox protection enabled, and has a responding
QEMU guest agent. UFW permits only LAN SSH and mDNS during the isolation phase.
SQL port 3306 and replication port 50051 are not open.

The `nas-backups` path between Sefer and the NAS uses 10 GbE. The post-seed
backup transferred the sparse 100 GiB disk in 83 seconds and produced a
3.49 GiB archive.

The service unit has a `ConditionPathExists=/etc/dolt/config.yaml` guard. The
cluster configuration does not yet exist, so the standby cannot accidentally
start or contact production.

## Migration phases

The executable activation and rollback checklist is maintained in
[DOLT_LIVE_REPLICA_PLAN.md](DOLT_LIVE_REPLICA_PLAN.md).

1. **Isolated base — complete.** Provision and harden the VM, pin Dolt 2.3.1,
   establish its reserved address, and keep all Dolt network services off.
2. **Restore and upgrade rehearsal — complete for the August 24 snapshot.** A
   disposable copy opened under 2.3.1 and passed full repository integrity
   validation.
3. **Fresh cold seed — complete.** The authorized pause produced a rollback
   snapshot and cold VM backup of the primary. Its data was copied
   byte-for-byte to Sefer and passed validation under Dolt 2.3.1.
4. **Production preparation — pending.** Upgrade the old primary in its own
   rollback-controlled maintenance window and pin both nodes identically.
5. **Direct standby — pending.** Configure per-database remotes and the cluster
   YAML, restrict replication traffic to the two peers, seed sequentially, and
   expose only a separate read endpoint such as `doltsvr-ro` after lag is clean.
6. **Controlled cutover — pending.** Pause writers, verify zero lag, perform the
   graceful epoch transition, move the canonical identity to Sefer, and retain
   the old server as rollback standby through the soak period.

## Fresh seed result

Production Dolt was stopped briefly on 2026-08-27 for an authorized cold-copy
window. Before copying, Seykhl received the rollback snapshot
`pre-fresh-seed-20260827`, and the NAS received this full VM archive:

`/mnt/proxmox-backups/doltsvr/vzdump/vzdump-qemu-100-2026_08_27-22_50_11.vma.zst`

The service-only outage was about four minutes. Production then returned on
Dolt 2.1.10 with the same configuration and is active as the write primary.

The archive was restored on Sefer as protected VM 123,
`doltsvr-fresh-seed-20260827`. VM 123 remains stopped, has no virtual NIC, and
has autostart disabled. Its `/home` filesystem was attached read-only to VM 100
and copied to `/home/doltdb/databases/doltsvr`; the source disk was then
unmounted and detached.

Fresh-seed verification on VM 100 found:

- 2.9 GiB copied, with an empty checksum-mode `rsync` dry run afterward
- 34 Dolt repositories validated with `dolt fsck` under Dolt 2.3.1
- Zero integrity failures
- `beads_yesod`: 4,154 issues on `main`
- `beads_yesod_work`: 114 issues on `main`
- `yesod_aicoe`: 2,079 issues on `main`
- `yesod_aicoe.prebloat.bak`: 42,113 reachable commit objects validated

A post-seed snapshot backup of VM 100 completed successfully at 23:03 and is
stored as:

`/mnt/proxmox-backups/dump/vzdump-qemu-100-2026_08_27-23_01_42.vma.zst`

The normal retention policy pruned the earlier, pre-seed VM 100 backup after
this newer backup completed.

## Analytics access

VM 100 currently contains a **static snapshot**, not a live read replica. It
does not receive production changes. The SQL service is disabled and inactive,
UFW does not allow port 3306, and no analytics credential exists yet.

For analytics that can use the 2026-08-27 snapshot, connect over SSH and run
read-only queries with the local Dolt CLI. For example:

```bash
ssh stephen@192.168.0.160
sudo -H -u dolt /usr/local/bin/dolt \
  --data-dir=/home/doltdb/databases/doltsvr \
  --use-db=beads_yesod \
  sql -q 'SELECT COUNT(*) FROM issues;'
```

The mDNS name `doltsvr-sefer.local` may be used instead of the IP on the local
network. Analytics users must limit this access to read-only SQL and must not
start `dolt-sql-server.service` or modify the data directory.

After direct replication is configured and verified, the intended
MySQL-compatible endpoint is `192.168.0.160:3306`. That endpoint and a separate
read-only credential will be created in the direct-standby phase; they do not
exist yet.

## Offline rehearsal result

The documented NAS SQL-dump mirror was empty during the 2026-08-27 rehearsal,
so the test used the application-consistent August 24 VM snapshot instead:

`/mnt/proxmox-backups/doltsvr/vzdump/vzdump-qemu-100-2026_08_24-02_00_02.vma.zst`

The snapshot was restored as protected VM 122,
`doltsvr-rehearsal-20260824`. VM 122 is stopped, has no virtual NIC, and has
autostart disabled. Its disk was attached read-only to VM 100, copied into:

`/home/doltdb/rehearsals/2026-08-24/databases/doltsvr`

The source disk was then unmounted and detached. The archived VM remains the
untouched rollback source. Results against the copied data with Dolt 2.3.1:

- 34 Dolt repositories discovered and validated with `dolt fsck`
- Zero integrity failures
- `beads_yesod`: 3,863 issues; `main` branch readable
- `beads_yesod_work`: 113 issues; `main` branch readable
- `yesod_aicoe`: 2,079 issues; `main` branch readable
- `yesod_aicoe.prebloat.bak`: 42,113 commit objects validated

Use `scripts/validate-dolt-data-dir` for the same offline check on later seeds.

A manual snapshot-mode backup then completed successfully with guest-agent
freeze/thaw. Its archive was later pruned by the normal retention policy after
the newer post-seed backup documented above completed.

## Verification commands

```bash
ssh root@sefer 'qm config 100'
ssh root@sefer 'qm agent 100 network-get-interfaces'
ssh stephen@192.168.0.160 'dolt version'
ssh stephen@192.168.0.160 'sudo ufw status verbose'
ssh stephen@192.168.0.160 'systemctl is-enabled dolt-sql-server.service'
```

Before direct replication is enabled, schedule the primary upgrade and cluster
work in an explicit maintenance window, then follow the official
[Dolt replication procedure](https://www.dolthub.com/docs/sql-reference/server/replication/).
