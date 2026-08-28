# Yesod Semantic Graph controller VM

**Last verified:** 2026-08-27

## Overview

`yesod-semantic-graph` is VM 121 on `sefer`. It is the isolated controller and
private PostgreSQL pipeline-state host for the Yesod semantic graph project.
Neo4j remains on VM 118 and is a disposable derived read model; VM 121 owns no
authoritative Yesod source data.

| Setting | Value |
|---|---|
| Proxmox host | `sefer` (`192.168.0.100`) |
| VMID / name | 121 / `yesod-semantic-graph` |
| Guest OS | Debian 13 (Trixie) |
| Resources | 4 vCPU, 8 GiB RAM, 64 GiB thin disk on redundant `vmdata` |
| LAN IP | Static `192.168.0.172/24`, gateway `192.168.0.1` |
| MAC | `BC:24:11:B8:5D:94` |
| Start policy | Starts with host; startup order 30; guest agent enabled |
| Protection | Proxmox deletion protection enabled |
| Tags | `yesod`, `semantic-graph` |

Do not place unrelated workloads on VM 121. The VM and its backup job are
intentionally scoped to this project.

## Access and service layout

Stephen's existing Ed25519 public key was injected with cloud-init; no private
key was copied to Sefer or the guest.

```bash
ssh stephen@192.168.0.172
ssh root@sefer 'qm status 121'
ssh root@sefer 'qm guest cmd 121 ping'
```

The guest uses the `America/Los_Angeles` timezone. Important paths are:

| Path | Purpose |
|---|---|
| `/opt/yesod-semantic-graph/releases/<commit>` | Immutable reviewed application releases |
| `/opt/yesod-semantic-graph/current` | Relative symlink to the active release |
| `/etc/yesod-semantic-graph/pipeline.env` | Protected runtime settings; no source credentials currently installed |
| `/var/lib/yesod-semantic-graph` | Service-account state and current artifact staging |
| `/var/backups/yesod-semantic-graph` | Local PostgreSQL custom-format dumps |

The initial application release is git commit `e162624134ce`. Application
deployment and migration commands are canonical in that repository's
`docs/deployment.md`.

## PostgreSQL boundary

PostgreSQL 17 runs on VM 121 and listens only on `127.0.0.1` and `::1`. The
database is `yesod_semantic_graph`, schema `pipeline`, and the matching Linux
and PostgreSQL account is `yesod_semantic_graph_pipeline`.

The role has no password and uses local Unix-socket peer authentication. It is
not a superuser and cannot create databases, roles, or replicas. No production
Yesod source credential is present on this VM.

The forward-only Alembic revision `0001_pipeline_ledger` is applied. It owns
six application tables plus its schema-local version table. Do not drop this
database just because Neo4j is disposable: the PostgreSQL ledger owns pipeline
resumability, lineage, and promotion reports.

## Neo4j dependency

VM 121 can reach VM 118 at:

- Browser/HTTP: `http://192.168.0.167:7474`
- Bolt: `bolt://192.168.0.167:7687`

The VM 118 authentication secret and container configuration were not changed
during provisioning. A scoped projector credential and TLS decision remain
application follow-ups.

## Backups

The guest timer `yesod-semantic-graph-backup.timer` creates a PostgreSQL
custom-format dump at 04:15 Pacific. Dumps are mode `0600`; the local job
removes files older than 14 days.

Sefer has a separate Proxmox job also named `yesod-semantic-graph`. It contains
only VM 121, runs at 04:30 Pacific, writes `zstd` snapshots to `nas-backups`,
and retains 7 daily, 4 weekly, and 3 monthly backups. The initial snapshot on
2026-08-27 completed successfully and used guest-agent filesystem freeze/thaw.

```bash
ssh stephen@192.168.0.172 \
  'systemctl list-timers yesod-semantic-graph-backup.timer --no-pager'
ssh root@sefer \
  'pvesh get /cluster/backup/yesod-semantic-graph --output-format json'
```

## Base image

VM 121 was built from the official Debian 13 generic AMD64 cloud image stored
at `/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2`. Its verified
SHA-512 is:

```text
720d9a2d21167e8aa1bb86a8a816658c7beaeec6975c376e15a0761383a869a466cbf7fe11c287c989020070309889dd81c37cd412290531245e3562334e05f3
```

The image was not cloned from runner template 9000, avoiding inherited runner
credentials or configuration.

## Remaining infrastructure follow-ups

- Reserve or exclude `192.168.0.172` for MAC `BC:24:11:B8:5D:94` in the
  router. The address was inactive and absent from the 2026-07-21 reservation
  export when VM 121 was created, but the router itself was not changed.
- Choose the final NAS path/mount for content-addressed artifacts before a
  production backfill. The current VM-local path is suitable only for the M1
  structured-spine work.
- Review LAN-only Bolt versus TLS when the projector is implemented. Do not
  expose VM 118 or VM 121 to an untrusted network without a firewall review.
