# Yesod Semantic Graph controller VM

The deployed symlink still targets `releases/dac21c562713`. Local PostgreSQL
17.11 is running, and the 04:15 Pacific logical backup completed successfully
on September 5. The M3 graph counts/digests below are historical acceptance
results, not a fresh projection audit. No rebuild or source-data query was run.

**Last verified:** 2026-09-05 (infrastructure; M3 acceptance remains dated August 30)

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
| Router reservation | Confirmed complete 2026-08-27 |
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
| `/etc/yesod-semantic-graph/source-production.env` | Dedicated audited production reader DSN over Tailscale |
| `/etc/yesod-semantic-graph/neo4j.env` | Protected trusted-TLS projector credential |
| `/var/lib/yesod-semantic-graph` | Service-account state and current artifact staging |
| `/var/backups/yesod-semantic-graph` | Local PostgreSQL custom-format dumps |

The active application release is git commit `dac21c562713`. Application
deployment, synthetic acceptance, and migration commands are canonical in that
repository's `docs/deployment.md`.

## PostgreSQL boundary

The authentication/role assertions below are the retained August acceptance
record. September checks verified the running local PostgreSQL listener and
backup result, not every role grant.

PostgreSQL 17 runs on VM 121 and listens only on `127.0.0.1` and `::1`. The
database is `yesod_semantic_graph`, schema `pipeline`, and the matching Linux
and PostgreSQL account is `yesod_semantic_graph_pipeline`.

The role has no password and uses local Unix-socket peer authentication. It is
not a superuser and cannot create databases, roles, or replicas.

A generated credential for the production login
`yesod_semantic_graph_source_reader` is installed in
`/etc/yesod-semantic-graph/source-production.env`. The file is
`root:yesod_semantic_graph_pipeline` mode `0640`; its non-secret fields target
database `stephen` at the source's explicit Tailscale address. The role passes
the semantic-graph capability audit: required table reads, no writes or
database/schema creation, no elevated attributes, no role memberships, and a
read-only transaction.

The separate `yesod_fixture` database contains only the committed sanitized
acceptance fixture. Login `yesod_semantic_graph_fixture_reader` has
`default_transaction_read_only=on`, database `CONNECT`, schema `USAGE`, and
table `SELECT`, with no create/write privileges. The pipeline-state role cannot
connect to this database.

The forward-only Alembic revision `0001_pipeline_ledger` is applied. It owns
six application tables plus its schema-local version table. Do not drop this
database just because Neo4j is disposable: the PostgreSQL ledger owns pipeline
resumability, lineage, and promotion reports.

## Production source connectivity

The production catalog runs on VM 102 (`yesod-postgres-server`) on Proxmox host
`sefer`. Its observed guest IPv4 is now `192.168.20.155`; PostgreSQL client
traffic uses the server's Tailscale address
`100.115.10.68:5432`. The source now also listens on the VLAN address; see
[YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md). Historical preflight
from VM 121 initially found:

- `192.168.0.155:5432`: connection refused;
- `100.115.10.68:5432`: unreachable without a tailnet route.

Tailscale 1.102.3 is installed from its stable Debian 13 repository on VM 121,
`tailscaled` is enabled, and the guest is enrolled. MagicDNS acceptance remains
disabled on this guest; the protected DSN uses the explicit source Tailscale
address to avoid the LAN hostname collision.

The August acceptance recorded the restricted reader role described in the
application repository's `docs/source-boundary.md`. TCP reachability and
`ysg source-audit` passed then; this September infrastructure audit did not
repeat that application capability audit.

The current production application password was also found in tracked
infrastructure Markdown. The plaintext copies are redacted in the current
tree, but the password remains in git history and must be rotated by the source
owner. Do not reuse that application identity for the semantic graph.

## Production plan proof

The reviewed, mutation-free production report is retained outside git at
`/var/lib/yesod-semantic-graph/reviews/production-plan-20260828T044213Z.json`.
It is owned by `yesod_semantic_graph_pipeline`, mode `0600`, with SHA-256
`9a22289549f2cfaab92e00a2aee184c62787173c642fdd6aeecd274a834495df`.

This was the pre-projection review report. It observed 2,115 source units and
produced a candidate with 5,945
nodes, 5,944 edges, 16,118 evidence assertions, and graph digest
`ddf27337487c46979c86a4215f29e251ff560f8a1907f7ab7e5be05caa534c78`.
A repeat produced identical counts and digest. That report itself caused no
artifact, pipeline-state, or Neo4j mutation; later guarded M2 and M3
acceptances superseded the six-node synthetic projection.

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

For the accepted M3 graph, VM 118 uses 6 GiB heap and 6 GiB page cache. The
prior 4 GiB/8 GiB Compose configuration is preserved at
`/opt/neo4j/compose.yaml.pre-m3-memory-20260830`. This narrow rebalance was
needed after a single large projection transaction filled the default
transaction-memory pool; the failed transaction rolled back cleanly.

## Synthetic rebuild proof

The live sanitized run produced active epoch
`epoch:127cfacfde2ecb3bbd25fe97` with digest
`9191fb01d6ab102c629269fbbbd5bb774e51c202c961c1385e34feb8f294db6a`.
It contains 6 domain nodes, 5 domain edges, and 12/12 resolved evidence
references. Acceptance deleted all 7 owned nodes (including epoch metadata),
rebuilt, and obtained the identical digest. The PostgreSQL ledger contains one
source unit, checkpoint, job, artifact, active epoch, and passing promotion
report. Raw fixture body/comment text is absent from the mode-`0600` artifact.

## Production M3 rebuild proof

The August 30 acceptance recorded epoch `epoch:ff074c8537e13d748f2cab6b`, produced by release
`dac21c562713` from 24,077 immutable source units and eight checkpoints. It
contains 138,879 domain nodes, 170,443 domain edges, and 389,993 resolved
evidence assertions. Its canonical digest is:

```text
67b8430f3b307ff0e678ca03a28c46d2943038a4def7858fe608aa03c045d9c9
```

The graph includes the M2 structured spine plus fresh committed-object code
snapshots for `yesod-aicoe` and `aicoe-bot`: 961 modules, 21,921
functions/symbols, 2,598 exact imports, 31,655 exact calls, 37,721
commit-to-current-symbol blame links, and two Git-proven renames.

Projector v3 deletes and creates in committed batches of 1,000. Full acceptance
is therefore a deliberate read-only maintenance window: readers can observe an
empty or partial owned graph until the second verified build is promoted. The
retained transient unit `ysg-m3-acceptance-r4.service` ran from 15:29:06 to
15:35:20 Pacific, peaked at 3.5 GiB controller memory, deleted 138,880 owned
nodes including epoch metadata, built twice to the same digest, and wrote
passing report `promotion-report:57cd8fac22a11c1abf20a0a0`.

Protected artifacts are outside git:

```text
/var/lib/yesod-semantic-graph/artifacts/graph_envelope/39/39c6c7018a24c9cb4d592b082a51c767d4afe34bfaf7ff19099536553dedd630.json
/var/lib/yesod-semantic-graph/artifacts/code-manifest/a7/a79f4a79d040c697e03cfe5f3deffbd62e180320843abaa4713d66c283d29c2e.json
```

## Backups

The guest timer `yesod-semantic-graph-backup.timer` creates a PostgreSQL
custom-format dump at 04:15 Pacific. Dumps are mode `0600`; the local job
removes files older than 14 days.

Sefer has a separate Proxmox job also named `yesod-semantic-graph`. It contains
only VM 121, runs at 04:30 Pacific, writes `zstd` snapshots to `nas-backups`,
and is configured to retain 7 daily, 4 weekly, and 3 monthly backups.
The September 5 VM backup wrote its archive but failed during NAS pruning;
see [BACKUPS.md](BACKUPS.md). The initial snapshot on
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

- Restrict the VM 121 tailnet ACL to the required
  `yesod-postgres-server:5432` path.
- Rotate the exposed production application password; it remains in git
  history even though the current tracked copies are redacted.
- Choose the final NAS path/mount for content-addressed artifacts before a
  production corpus backfill. The current VM-local path is sufficient for the
  accepted deterministic M1–M3 artifacts, not corpus-scale M4/M5 payloads.
- Neo4j Browser remains plaintext HTTP on the trusted LAN. Do not expose VM 118
  or VM 121 to an untrusted network without a firewall review.
