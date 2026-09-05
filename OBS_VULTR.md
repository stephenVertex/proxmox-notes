# obs-vultr — SigNoz Observability Stack

VM 117 remains on Sefer `vmbr0`; its guest IP and Tailscale bindings below
are unchanged. The configured nightly VM backup is not a clean success: September 5 archive transfer completed but NAS pruning failed. See [BACKUPS.md](BACKUPS.md).

**Last verified:** 2026-09-05

## Overview

`obs-vultr` is VM 117 on `sefer` and runs the self-hosted SigNoz observability
stack in Docker Compose. Despite its name, the VM is now on the on-premises
Proxmox host, not Vultr.

| Setting | Value |
|---|---|
| Proxmox host | `sefer` (`192.168.0.100`) |
| VMID / name | 117 / `obs-vultr` |
| Guest OS | Debian 13 (Trixie) |
| Resources | 8 vCPU, 16 GiB RAM, 120 GiB disk on `vmdata` |
| LAN IP | `192.168.0.163` |
| Tailscale IP | `100.115.156.60` |
| Start policy | Starts with the Proxmox host |

## Services and access

The externally exposed endpoints are bound to the Tailscale address rather
than the LAN address:

| Endpoint | Address | Purpose |
|---|---|---|
| SigNoz UI | `http://100.115.156.60:8080` | Observability UI |
| OpenTelemetry gRPC | `100.115.156.60:4317` | OTLP ingestion |
| OpenTelemetry HTTP | `100.115.156.60:4318` | OTLP ingestion |

The SigNoz UI returned HTTP 200. Docker reports the UI, ClickHouse,
PostgreSQL and Keeper healthy; the
ingester is running. The completed migrator and user-script containers have
exit code 0. The active Compose containers are:

- `signoz-signoz-0` — `signoz/signoz:v0.137.0`
- `signoz-ingester-1` — `signoz/signoz-otel-collector:v0.144.8`
- `signoz-telemetrystore-clickhouse-0-0` — ClickHouse 25.12.5
- `signoz-metastore-postgres-0` — PostgreSQL 16
- `signoz-telemetrykeeper-clickhousekeeper-0` — ClickHouse Keeper 25.12.5

All have Docker’s `unless-stopped` restart policy. The Compose deployment and
configuration bind mounts live under `/opt/signoz/pours/deployment/`.

## Data and backup

Persistent SigNoz data is in Docker volumes, including:

- `signoz-telemetrystore-0-0-data` (ClickHouse data)
- `signoz-metastore-postgres-0-data` (PostgreSQL metadata)
- `signoz-telemetrykeeper-0-data` (ClickHouse Keeper)

VM 117 is included in the nightly 03:30 `sefer-light-services` snapshot job
to `nas-backups` (7 daily, 4 weekly, 3 monthly). Use the service’s documented
application-consistent backup/recovery procedure before relying on a restore
for telemetry data.

## Operations

```bash
ssh root@sefer "qm status 117"
ssh root@sefer "qm guest exec 117 -- docker ps"
```

The QEMU guest agent was functioning during the last inventory.
