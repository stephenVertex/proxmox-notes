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
| `/etc/yesod-semantic-graph/pipeline.env` | Protected pipeline-state and local path settings |
| `/etc/yesod-semantic-graph/source.env` | Protected synthetic fixture read-only DSN |
| `/etc/yesod-semantic-graph/neo4j.env` | Protected trusted-TLS projector credential |
| `/var/lib/yesod-semantic-graph` | Service-account state and current artifact staging |
| `/var/backups/yesod-semantic-graph` | Local PostgreSQL custom-format dumps |

The active application release is git commit `50217d2b01a8`. Application
deployment, synthetic acceptance, and migration commands are canonical in that
repository's `docs/deployment.md`.

## PostgreSQL boundary

PostgreSQL 17 runs on VM 121 and listens only on `127.0.0.1` and `::1`. The
database is `yesod_semantic_graph`, schema `pipeline`, and the matching Linux
and PostgreSQL account is `yesod_semantic_graph_pipeline`.

The role has no password and uses local Unix-socket peer authentication. It is
not a superuser and cannot create databases, roles, or replicas. No production
Yesod source credential is present on this VM.

The separate `yesod_fixture` database contains only the committed sanitized
acceptance fixture. Login `yesod_semantic_graph_fixture_reader` has
`default_transaction_read_only=on`, database `CONNECT`, schema `USAGE`, and
table `SELECT`, with no create/write privileges. The pipeline-state role cannot
connect to this database.

The forward-only Alembic revision `0001_pipeline_ledger` is applied. It owns
six application tables plus its schema-local version table. Do not drop this
database just because Neo4j is disposable: the PostgreSQL ledger owns pipeline
resumability, lineage, and promotion reports.

## Neo4j dependency

VM 121 reaches VM 118 at:

- Browser/HTTP: `http://192.168.0.167:7474`
- Projector Bolt: `bolt+s://192.168.0.167:7687`

Bolt TLS is required and plaintext Bolt was verified rejected. The private
local CA stays on VM 118; its public certificate is installed in VM 121's
system trust store. `/etc/yesod-semantic-graph/neo4j.env` holds the dedicated
`yesod_semantic_graph_projector` login. Neo4j Community has no RBAC, so this
identity cannot be privilege-restricted inside Neo4j; effective scope comes
from the single-purpose disposable VM and owner-tagged projector code.

## Synthetic rebuild proof

The live sanitized run produced active epoch
`epoch:127cfacfde2ecb3bbd25fe97` with digest
`9191fb01d6ab102c629269fbbbd5bb774e51c202c961c1385e34feb8f294db6a`.
It contains 6 domain nodes, 5 domain edges, and 12/12 resolved evidence
references. Acceptance deleted all 7 owned nodes (including epoch metadata),
rebuilt, and obtained the identical digest. The PostgreSQL ledger contains one
source unit, checkpoint, job, artifact, active epoch, and passing promotion
report. Raw fixture body/comment text is absent from the mode-`0600` artifact.

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
- Neo4j Browser remains plaintext HTTP on the trusted LAN. Do not expose VM 118
  or VM 121 to an untrusted network without a firewall review.
