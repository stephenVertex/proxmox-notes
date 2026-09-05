# LiteLLM gateway

**Last verified:** 2026-09-05 via Sefer guest agent and Docker metadata.

## Deployment

| Setting | Value |
|---|---|
| Proxmox host / VM | Sefer / 101 `litellm-gateway` |
| Guest | Debian 13 |
| CPU / RAM | 2 host vCPU; 4 GiB maximum, 2 GiB balloon minimum |
| Disk | 64 GiB on `vmdata` |
| LAN / Tailscale | `192.168.0.157` / `100.84.120.44` |
| Network | Sefer `vmbr0`; MAC `BC:24:11:85:BD:D3` |
| Boot | Autostart enabled, responding QEMU guest agent |
| Compose directory | `/opt/litellm/deploy` |

This is distinct from stopped Seykhl VM 113 `litellm-broker-staging`.
Seykhl VM 101 is the stopped Jeffrey development guest; always qualify VMIDs
with their host.

## Running stack

| Container suffix | Image | Observed state |
|---|---|---|
| `caddy-1` | `caddy:2.10-alpine` | Running; host TCP 443 published |
| `bootstrap-broker-1` | `litellm-gateway-bootstrap-broker` | Healthy; internal port 8080 |
| `dashboard-collector-1` | `litellm-dashboard-collector:local` | Healthy |
| `dashboard-usage-collector-1` | `litellm-dashboard-collector:local` | Healthy |
| `litellm-1` | `ghcr.io/berriai/litellm:v1.98.0` | Healthy; internal port 4000 |
| `postgres-1` | `postgres:17-alpine` | Healthy; internal port 5432 |

All names have prefix `litellm-gateway-`; all use restart policy
`unless-stopped`. The unused guest-native PostgreSQL 17 cluster is down;
the stack's database is the healthy Docker PostgreSQL container.

## Configuration and state

Caddy mounts `/opt/litellm/deploy/Caddyfile.production`, `dashboard.caddy`,
`/opt/litellm/dashboard/static`, `dashboard-data`, and certificates under
`/opt/litellm/tailscale-certs`. The LiteLLM config is
`/opt/litellm/deploy/config.yaml`. The bootstrap broker mounts the protected
`claude-token-pool.toml` and a public CA file. No credential values were read
into this documentation.

Persistent Docker volumes include `litellm-gateway_postgres-data`,
`litellm-gateway_chatgpt-auth`, and Caddy data/config. Collector output is
under `/opt/litellm/deploy/dashboard-data`.

Container health and socket publication were verified. Authenticated model
requests, provider billing, dashboard data accuracy and the intended HTTPS
hostname were not tested; do not infer those from Docker's healthy status.
VM 101 is absent from Sefer's current scheduled backups. See [BACKUPS.md](BACKUPS.md).

## Read-only operations

```bash
ssh -o BatchMode=yes root@sefer 'qm status 101'
ssh -o BatchMode=yes root@sefer 'qm guest exec 101 -- docker ps'
ssh -o BatchMode=yes root@sefer 'qm guest exec 101 -- systemctl list-timers litellm-tailscale-cert.timer --no-pager'
```

Review the deployed Compose files and current active requests before any
restart, rebuild or credential change; the stopped staging guest is not a
substitute for the production gateway.
