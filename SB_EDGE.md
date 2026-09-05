# sb-edge — Supabase APIs and Edge Runtime

**Last verified:** 2026-09-05 from VM 111, nginx routing, listeners and containers.

## Deployment

`sb-edge` now runs as **Sefer VM 111**. Its old Seykhl copy is stopped and
renamed `do-not-start`. Never start both copies with the same network identity.

| Setting | Value |
|---|---|
| Guest / resources | Debian 13; 2 host vCPU, 4 GiB RAM, 20 GiB disk |
| Storage | `vmdata:vm-111-disk-0` |
| Bridge / LAN | Sefer `vmbr0` / `192.168.0.137` |
| MAC | `BC:24:11:5E:D5:A8` |
| Tailscale | `100.115.156.68`, `sb-edge.tailb4b58.ts.net` |
| Boot policy | `onboot` omitted (manual start); QEMU agent configured but not running |
| Administration | `ssh -o BatchMode=yes stephen@192.168.0.137` |

The database service has moved to Sefer VM 102. Its current VLAN address is
`192.168.20.155`; the existing Tailscale endpoint is `100.115.10.68:5432`.
The old `192.168.0.155` address is obsolete. This audit did not expose or
rewrite application DSNs. See [YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md).

## Current API routes

Tailscale Serve has these configured HTTPS routes:

| Tailnet route | Local proxy |
|---|---|
| `https://sb-edge.tailb4b58.ts.net/` | `http://127.0.0.1:8000` |
| `https://sb-edge.tailb4b58.ts.net/clip/` | `http://127.0.0.1:8001` |

nginx exposes two stacks:

| nginx port / path | Backend | Purpose |
|---|---|---|
| 8000 `/rest/v1/` | `localhost:3000` | Original PostgREST / sjbgtd |
| 8000 `/functions/v1/` | `localhost:9000/functions/v1/` | Original edge functions |
| 8001 `/rest/v1/` | `localhost:3001` | Clip PostgREST |
| 8001 `/functions/v1/` | `localhost:9001/functions/v1/` | Clip edge functions |
| 8001 `/storage/v1/` | `localhost:5000` | Clip Storage API |
| 8001 `/realtime/v1/` | `localhost:4000` | Clip Realtime |

These nginx/backend TCP ports bind all guest interfaces. Realtime publishes
port 4000 through Docker, which need not appear as a userspace listener in
`ss`. Routing configuration and process state do not prove authenticated API
or database operations succeed.

## Service state

nginx, `postgrest`, `postgrest-clip`, `storage-clip`, `realtime-clip` and
`supabase-edge-runtime-clip` were active; ports 9000 and 9001 both listened.
The `realtime-clip` Docker container uses `supabase/realtime:latest`.
Both edge-runtime service units are enabled.

**Degraded component:** `postgrest-sjb-social.service` was in
`activating/auto-restart`, result `exit-code`, with more than 82,000 recorded
restarts. Treat social API health separately from the other running components.
Follow-up: `proxmox-3tg`. No restart or functional API mutation was performed
during the audit.

## Files and functions

The original function tree remains `/home/stephen/functions/`, with `main`,
`available-actions`, `check-capture`, `create-capture`, `template-dag`,
`update-capture` and `hello`. The original PostgREST configuration lives under
`/opt/postgrest`; active nginx routing is in `/etc/nginx/sites-enabled/`.

Service environment files contain database/API credentials. Keep those values
out of documentation and shell output. The older binary installation notes
remain in [SUPABASE_EDGE_RUNTIME.md](SUPABASE_EDGE_RUNTIME.md) as a historical
provisioning record; they do not describe the expanded live stack by themselves.

## Backups and operations

VM 111 is not in either current Sefer backup job. The stopped Seykhl copy is
not a backup of current state. See [BACKUPS.md](BACKUPS.md).

```bash
ssh -o BatchMode=yes stephen@192.168.0.137 \
  'systemctl show postgrest-sjb-social -p ActiveState -p SubState -p NRestarts -p Result'
ssh -o BatchMode=yes stephen@192.168.0.137 'sudo -n tailscale serve status'
ssh -o BatchMode=yes stephen@192.168.0.137 'sudo -n nginx -t; sudo -n docker ps'
```
