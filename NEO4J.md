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
| Bolt | `bolt://192.168.0.167:7687` | Exposed on all guest interfaces |

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
- `secrets/neo4j_auth.txt` → `/run/secrets/neo4j_auth`

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
