# neo4j — Graph Database VM

**Last verified:** 2026-08-27

## Overview

`neo4j` is VM 118 on `sefer`. It runs a single Neo4j Docker container for the
graph database workload.

| Setting | Value |
|---|---|
| Proxmox host | `sefer` (`192.168.0.100`) |
| VMID / name | 118 / `neo4j` |
| Guest OS | Debian 13 (Trixie) |
| Resources | 4 vCPU, 16 GiB RAM, 100 GiB disk on `vmdata` |
| LAN IP | `192.168.0.167` |
| Start policy | Starts with the Proxmox host |

## Service and access

The active container is `neo4j`, running image `neo4j:2026.07.1` with Docker’s
`unless-stopped` restart policy.

| Protocol | Endpoint | Notes |
|---|---|---|
| Neo4j Browser / HTTP | `http://192.168.0.167:7474` | Exposed on all guest interfaces |
| Bolt | `bolt+s://192.168.0.167:7687` | TLS required; leaf SAN includes `192.168.0.167` |

The database is not currently published through a Cloudflare Tunnel or
Tailscale address. Treat the LAN exposure as trusted-network-only and restrict
it with the guest or Proxmox firewall before allowing untrusted devices on the
LAN.

## Data and backup

The container uses bind mounts under `/opt/neo4j/`:

- `data` → `/data`
- `import` → `/import`
- `logs` → `/logs`
- `plugins` → `/plugins`
- `certificates` → `/ssl` (read-only in the container)
- `secrets/neo4j_auth.txt` → `/run/secrets/neo4j_auth`

Bolt uses a VM-local CA under `/opt/neo4j/certificates/ca` and a server leaf
under `/opt/neo4j/certificates/bolt`. The leaf expires 2028-11-30. The original
Compose file is preserved as
`/opt/neo4j/compose.yaml.pre-ysg-tls-20260827`. Plaintext Bolt was verified
rejected; VM 121 trusts only the public CA certificate.

## Yesod semantic graph projection

The native user `yesod_semantic_graph_projector` is dedicated to the Yesod
semantic graph controller. Its password is stored only in VM 121's protected
`/etc/yesod-semantic-graph/neo4j.env`; the temporary transfer copy on VM 118 was
removed after verification.

Neo4j Community 2026.07.1 has no roles/RBAC and reports `NULL` roles for native
users, so the dedicated identity still has implied administrative capability.
Do not treat it as a database-enforced least-privilege account. Isolation is
provided by this single-purpose disposable VM and by projector operations being
limited to `_projection_owner=yesod-semantic-graph`. Use Enterprise or another
dedicated instance if strong multi-tenant authorization is required.

The accepted sanitized fixture currently has 7 owned nodes (6 domain plus one
epoch node), 11 owned relationships (5 domain plus 6 epoch memberships), and 23
label uniqueness constraints. Domain digest:
`9191fb01d6ab102c629269fbbbd5bb774e51c202c961c1385e34feb8f294db6a`.

The first live acceptance attempt failed closed before commit because Neo4j
2026 treated a returned `relationship` alias as a string in `ORDER BY`. The
graph remained at 0 nodes/0 relationships. Commit `99e8d6e` separated the
relationship type/property aliases; final release `50217d2b01a8` also removed
the replacement expression's deprecation warning. Repeated delete/rebuild runs
then produced the identical digest.

VM 118 is included in the nightly 03:30 `sefer-light-services` snapshot job
to `nas-backups` (7 daily, 4 weekly, 3 monthly). Do not treat a VM snapshot as
the only recovery plan for a graph database; use `neo4j-admin database dump`
or another application-consistent backup before upgrades or destructive work.

## Operations

```bash
ssh root@sefer "qm status 118"
ssh root@sefer "qm guest exec 118 -- docker ps"
```

The QEMU guest agent was functioning during the last inventory. Create a
verified SSH alias only after validating its current host key.
