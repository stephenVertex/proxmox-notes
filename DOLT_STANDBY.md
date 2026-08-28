# Dolt standby on Sefer

**Last verified:** 2026-08-27

## Safety boundary

The production `doltsvr` at `192.168.0.150` remains the only write primary.
Its Dolt process, systemd service, configuration, data directory, hostname, and
client routing must not be changed while the current complex job is active.

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

The service unit has a `ConditionPathExists=/etc/dolt/config.yaml` guard. The
cluster configuration does not yet exist, so the standby cannot accidentally
start or contact production.

## Migration phases

1. **Isolated base — complete.** Provision and harden the VM, pin Dolt 2.3.1,
   establish its reserved address, and keep all Dolt network services off.
2. **Restore and upgrade rehearsal — complete for the August 24 snapshot.** A
   disposable copy opened under 2.3.1 and passed full repository integrity
   validation. A final fresh Dolt-native seed is still required after the
   active production job.
3. **Production preparation — blocked by the active job.** After the job ends,
   take a VM snapshot and Dolt-native backups, upgrade the old primary in its
   own rollback-controlled maintenance window, and pin both nodes identically.
4. **Direct standby — pending.** Configure per-database remotes and the cluster
   YAML, restrict replication traffic to the two peers, seed sequentially, and
   expose only a separate read endpoint such as `doltsvr-ro` after lag is clean.
5. **Controlled cutover — pending.** Pause writers, verify zero lag, perform the
   graceful epoch transition, move the canonical identity to Sefer, and retain
   the old server as rollback standby through the soak period.

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
freeze/thaw. It produced the 1.97 GiB archive:

`/mnt/proxmox-backups/dump/vzdump-qemu-100-2026_08_27-22_37_37.vma.zst`

## Verification commands

```bash
ssh root@sefer 'qm config 100'
ssh root@sefer 'qm agent 100 network-get-interfaces'
ssh stephen@192.168.0.160 'dolt version'
ssh stephen@192.168.0.160 'sudo ufw status verbose'
ssh stephen@192.168.0.160 'systemctl is-enabled dolt-sql-server.service'
```

Before direct replication is enabled, confirm the production job has finished
and follow the official [Dolt replication procedure](https://www.dolthub.com/docs/sql-reference/server/replication/).
