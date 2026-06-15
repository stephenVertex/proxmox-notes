# sb-edge — Supabase Edge Runtime

**Document Version:** 2026-06-15
**VM ID:** 111
**Proxmox Node:** seykhl (192.168.0.202)

---

## Overview

`sb-edge` is a Debian 13 VM running a self-hosted **Supabase Edge Runtime** stack. It provides:

- **PostgREST** (port 3000) — REST API for PostgreSQL
- **Edge Runtime** (port 9000) — Deno-based serverless functions
- **nginx** (port 8000) — Reverse proxy combining both APIs
- **Tailscale Serve** (port 443) — HTTPS access within the tailnet

The database backend is `yesod-postgres-server` (192.168.0.155:5432).

---

## Network

| Interface | Value |
|-----------|-------|
| **LAN IP** | 192.168.0.137 |
| **Tailscale IP** | 100.115.156.68 |
| **Tailscale HTTPS** | https://sb-edge.tailb4b58.ts.net |
| **MAC Address** | bc:24:11:5e:d5:a8 |
| **Hostname** | sb-edge |

---

## Access

### SSH
```bash
ssh stephen@192.168.0.137
# or via Tailscale
ssh stephen@100.115.156.68
```

### HTTPS (Tailscale)
Any device on the tailnet can reach:
```
https://sb-edge.tailb4b58.ts.net/rest/v1/       # PostgREST API
https://sb-edge.tailb4b58.ts.net/functions/v1/  # Edge Functions
```

### HTTP (LAN only)
```
http://192.168.0.137:8000/rest/v1/
http://192.168.0.137:8000/functions/v1/
```

---

## Services

| Service | Port | Type | Description |
|---------|------|------|-------------|
| nginx | 8000 | Reverse Proxy | Routes `/rest/v1/` → PostgREST, `/functions/v1/` → Edge Runtime |
| PostgREST | 3000 | REST API | Auto-generated REST API from PostgreSQL schema |
| Edge Runtime | 9000 | Function Runtime | Deno-based serverless functions |
| Tailscale Serve | 443 | HTTPS Proxy | Tailscale-managed HTTPS within tailnet |

---

## Edge Functions

Located in `/home/stephen/functions/`:

| Function | Path | Description |
|----------|------|-------------|
| **main** | `/home/stephen/functions/main/index.ts` | Router/entrypoint — dispatches requests to other functions |
| **available-actions** | `/home/stephen/functions/available-actions/index.ts` | Polling endpoint for agents to discover unblocked actions |
| **check-capture** | `/home/stephen/functions/check-capture/` | Capture checking logic |
| **create-capture** | `/home/stephen/functions/create-capture/` | Capture creation logic |
| **template-dag** | `/home/stephen/functions/template-dag/` | Template DAG processing |
| **update-capture** | `/home/stephen/functions/update-capture/` | Capture update logic |
| **hello** | `/home/stephen/functions/hello/` | Test/healthcheck function |

---

## Configuration

### Environment Variables

**File:** `/home/stephen/functions/.env`

```
SUPABASE_URL=http://localhost:8000
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.M4aQ5FdNIpvV2I2kWY5JnLSEErAQoWLMVGlEUQXnKUo
```

### PostgREST Config

**File:** `/opt/postgrest/postgrest.conf`

```
db-uri = "$(PGRST_DB_URI)"
db-schemas = "public"
db-anon-role = "anon"
db-pool = 15
jwt-secret = "$(PGRST_JWT_SECRET)"
server-port = 3000
```

The database URI points to `yesod-postgres-server` at 192.168.0.155:5432.

### nginx Config

**File:** `/etc/nginx/sites-available/supabase-proxy`

```nginx
server {
    listen 8000;
    server_name localhost;

    location /rest/v1/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /functions/v1/ {
        proxy_pass http://localhost:9000/functions/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
```

---

## Systemd Services

| Service | File | Status |
|---------|------|--------|
| **nginx** | `/etc/systemd/system/nginx.service` | Enabled, Active |
| **postgrest** | `/etc/systemd/system/postgrest.service` | Enabled, Active |
| **supabase-edge-runtime** | `/etc/systemd/system/supabase-edge-runtime.service` | Enabled, Active |
| **tailscale-serve** | `/etc/systemd/system/tailscale-serve.service` | Enabled, Active |
| **tailscaled** | `/usr/lib/systemd/system/tailscaled.service` | Enabled, Active |

---

## Tailscale Setup

**Installed:** 2026-06-15
**Version:** 1.98.4

```bash
# Authenticated with auth key
sudo tailscale up --authkey=<key>

# Serve HTTPS on port 8000
sudo tailscale serve 8000

# Systemd service for persistence
sudo systemctl enable tailscale-serve.service
sudo systemctl start tailscale-serve.service
```

---

## Verification Commands

```bash
# Check all services
sudo systemctl status nginx postgrest supabase-edge-runtime tailscale-serve

# Test PostgREST API
curl https://sb-edge.tailb4b58.ts.net/rest/v1/

# Test Edge Function
curl https://sb-edge.tailb4b58.ts.net/functions/v1/hello

# Check Tailscale status
sudo tailscale status

# Check Tailscale serve
sudo tailscale serve status

# View edge runtime logs
sudo tail -f /var/log/supabase-edge-runtime.log
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u supabase-edge-runtime.service -f
sudo journalctl -u postgrest.service -f
sudo journalctl -u tailscale-serve.service -f

# Check nginx config
sudo nginx -t
sudo systemctl restart nginx
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql postgresql://stephen:lj*123NM@yesod-postgres-server:5432/stephen -c "SELECT 1"

# Check PostgREST logs
sudo journalctl -u postgrest.service -n 50
```

### Tailscale Issues
```bash
# Check Tailscale status
sudo tailscale status

# Reset and restart serve
sudo tailscale serve reset
sudo systemctl restart tailscale-serve.service

# Check if port 443 is available
sudo ss -tlnp | grep 443
```

---

## Related Systems

- **Database:** `yesod-postgres-server` (192.168.0.155:5432)
- **Proxmox Node:** `seykhl` (192.168.0.202)
- **Tailscale Network:** `stephen.devices` (tailb4b58.ts.net)

---

## Quick Reference

```bash
# SSH to sb-edge
ssh stephen@sb-edge

# Restart all services
sudo systemctl restart nginx postgrest supabase-edge-runtime tailscale-serve

# Test API
curl https://sb-edge.tailb4b58.ts.net/rest/v1/

# Test function
curl https://sb-edge.tailb4b58.ts.net/functions/v1/hello
```
