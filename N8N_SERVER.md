# n8n-server — n8n Automation Platform

**Last verified:** 2026-09-05. n8n is version `2.8.4`; n8n, Caddy and
cloudflared are active. Local `/healthz` and public HTTPS both return 200.
VM 107 remains on Sefer `vmbr0` at `192.168.0.145`; its QEMU guest agent is
not running. The configured nightly VM backup is not a clean success: September 5 archive transfer completed but NAS pruning failed. See [BACKUPS.md](BACKUPS.md).

## Overview
`n8n-server` (VMID 107) is a dedicated n8n automation server running on Proxmox host `sefer`. It provides a self-hosted workflow automation platform.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 107 |
| **Name** | n8n-server |
| **OS** | Debian 12 (Linux L26) |
| **CPU** | x86-64-v2-AES |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 30GB (`vmdata`, scsi0) |
| **Network** | vmbr0 (DHCP), virtio |
| **MAC** | BC:24:11:3B:86:22 |
| **LAN IP** | 192.168.0.145 |
| **Status** | Running |
| **Template** | No |
| **Cloud-Init** | Enabled (user: stephen) |

## Access

### n8n Web Interface (HTTPS) ✅
- **URL:** https://n8n.meshcrawler.com
- **Auth:** n8n built-in user management (owner: stephen@meshcrawler.com)
- **Note:** Basic auth in systemd service is legacy; n8n's own user management is primary auth
- **TLS:** Cloudflare-managed HTTPS; public route returned 200 at verification

### Local Access (Alternative)
- **URL:** https://192.168.0.145
- **Note:** Uses self-signed Caddy certificate — browsers will show a warning

### SSH
```bash
ssh stephen@192.168.0.145
```

### Proxmox Console
```bash
ssh root@sefer "qm console 107"
```

## Network Details
- **LAN IP:** 192.168.0.145 (assigned via DHCP)
- **MAC:** BC:24:11:3B:86:22
- **Bridge:** vmbr0
- **DNS:** n8n-server → 192.168.0.145

## Service Details
- **Service:** n8n (systemd)
- **Port:** 5678 (`*:5678` wildcard listener observed; not loopback-only)
- **Process:** Node.js (n8n)
- **Version:** 2.8.4
- **Data Directory:** /home/stephen/.n8n
- **Logs:** `sudo journalctl -u n8n -f`

### n8n Environment Variables (systemd)
| Variable | Value | Purpose |
|----------|-------|---------|
| `NODE_ENV` | `production` | Node environment |
| `N8N_BASIC_AUTH_ACTIVE` | `true` | Enable basic auth |
| `N8N_BASIC_AUTH_USER` | (set in service) | Auth username |
| `N8N_BASIC_AUTH_PASSWORD` | (set in service) | Auth password |
| `N8N_HOST` | `127.0.0.1` | Configured host value; actual TCP listener is wildcard |
| `N8N_PORT` | `5678` | Listen port |
| `N8N_EDITOR_BASE_URL` | `https://n8n.meshcrawler.com` | Public URL — tells n8n it's behind HTTPS proxy |
| `N8N_SECURE_COOKIE` | `false` | Current deployed value; not a loopback-binding guarantee |

> **Live binding check:** `ss -lnt` shows `*:5678`, despite `N8N_HOST=127.0.0.1`.
> The earlier claim of loopback-only binding was incorrect. The configured
> cookie setting does not establish network isolation; review the actual
> listening-address and firewall configuration before relying on that boundary.
> Follow-up: `proxmox-4km`.

## Reverse Proxy (Cloudflare Tunnel)
- **Service:** cloudflared (systemd)
- **Config:** /etc/cloudflared/config.yml
- **Public Hostname:** `n8n.meshcrawler.com` → `http://localhost:5678`
- **TLS:** Valid certificate via Cloudflare (auto-managed)
- **Logs:** `sudo journalctl -u cloudflared -f`

### Cloudflare Tunnel Configuration
```yaml
tunnel: 6b2b99a2-4fb1-4e88-be58-fca8b9d6fd2e
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: n8n.meshcrawler.com
    service: http://localhost:5678
  - service: http_status:404
```

Cloudflare Tunnel handles HTTPS termination and proxies requests to n8n on localhost:5678. No port forwarding needed.

## Reverse Proxy (Caddy — Optional Local Access)
- **Service:** caddy (systemd)
- **Port:** 443 (HTTPS)
- **Config:** /etc/caddy/Caddyfile
- **TLS:** Self-signed certificate via Caddy's internal CA
- **Note:** Only needed for local network access; not required for public access

### Caddy Configuration
```
192.168.0.145 {
    tls internal
    reverse_proxy localhost:5678
}
```

## Maintenance
```bash
# Check service status
ssh stephen@192.168.0.145 "sudo systemctl status n8n"
ssh stephen@192.168.0.145 "sudo systemctl status caddy"

# Restart n8n
ssh stephen@192.168.0.145 "sudo systemctl restart n8n"

# Restart Caddy
ssh stephen@192.168.0.145 "sudo systemctl restart caddy"

# View logs
ssh stephen@192.168.0.145 "sudo journalctl -u n8n -f"
ssh stephen@192.168.0.145 "sudo journalctl -u caddy -f"

# Update n8n
ssh stephen@192.168.0.145 "sudo npm install -g n8n && sudo systemctl restart n8n"

# Check n8n version
ssh stephen@192.168.0.145 "n8n --version"

# Test HTTPS
ssh stephen@192.168.0.145 "curl -k https://192.168.0.145"
```

## Management Commands
```bash
# Start VM
ssh root@sefer "qm start 107"

# Stop VM
ssh root@sefer "qm stop 107"

# Restart VM
ssh root@sefer "qm restart 107"

# Check status
ssh root@sefer "qm status 107"

# Get IP
ssh root@sefer "ip neigh | grep bc:24:11:3b:86:22"
```

## Notes
- n8n is installed directly via npm (no Docker)
- Runs as a systemd service for auto-start on boot
- Basic auth is enabled in systemd (legacy); n8n built-in user management is primary auth
- Owner account: stephen@meshcrawler.com (password reset 2026-07-26, DB backup on server)
- SQLite is used for the database (default n8n setup)
- Python task runner is not configured (JS task runner is active)
- Public HTTPS uses Cloudflare Tunnel; optional local HTTPS uses Caddy internal TLS
- n8n listens on `*:5678`; Cloudflare/Caddy use its loopback endpoint, but that does not prevent direct access through other guest interfaces.

## To Do
- [ ] Disable legacy basic auth in systemd (N8N_BASIC_AUTH_ACTIVE=false) once n8n user management confirmed working
- [ ] Configure n8n for production use (webhook URL, etc.)
- VM 107 is included in the scheduled Sefer backup; see [BACKUPS.md](BACKUPS.md) for current pruning failures and application-backup limits.
- [x] HTTPS/TLS configured via Caddy
- [x] Secure cookie issue fixed (N8N_EDITOR_BASE_URL + N8N_SECURE_COOKIE=false)
- [x] Owner password reset (2026-07-26)
- [ ] Configure external task runner if needed
- Public domain `n8n.meshcrawler.com` is already configured with Cloudflare TLS.
