# n8n-server — n8n Automation Platform

## Overview
`n8n-server` (VMID 107) is a dedicated n8n automation server running on Proxmox host `seykhl`. It provides a self-hosted workflow automation platform.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 107 |
| **Name** | n8n-server |
| **OS** | Debian 12 (Linux L26) |
| **CPU** | x86-64-v2-AES |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 30GB (local-lvm, scsi0) |
| **Network** | vmbr0 (DHCP), virtio |
| **MAC** | BC:24:11:3B:86:22 |
| **LAN IP** | 192.168.0.145 |
| **Status** | Running |
| **Template** | No |
| **Cloud-Init** | Enabled (user: stephen) |

## Access

### n8n Web Interface (HTTPS)
- **URL:** https://192.168.0.145
- **Basic Auth:** admin / admin
- **Note:** The default credentials are set in the systemd service. Change these for production use.
- **TLS:** Self-signed certificate via Caddy (internal CA). Browsers will show a warning — click "Advanced" → "Proceed" to access.

### SSH
```bash
ssh stephen@192.168.0.145
```

### Proxmox Console
```bash
ssh root@192.168.0.202 "qm console 107"
```

## Network Details
- **LAN IP:** 192.168.0.145 (assigned via DHCP)
- **MAC:** BC:24:11:3B:86:22
- **Bridge:** vmbr0
- **DNS:** n8n-server → 192.168.0.145

## Service Details
- **Service:** n8n (systemd)
- **Port:** 5678 (localhost only — not exposed externally)
- **Process:** Node.js (n8n)
- **Data Directory:** /home/stephen/.n8n
- **Logs:** `sudo journalctl -u n8n -f`

## Reverse Proxy (Caddy)
- **Service:** caddy (systemd)
- **Port:** 443 (HTTPS)
- **Config:** /etc/caddy/Caddyfile
- **TLS:** Self-signed certificate via Caddy's internal CA
- **Logs:** `sudo journalctl -u caddy -f`

### Caddy Configuration
```
192.168.0.145 {
    tls internal
    reverse_proxy localhost:5678
}
```

Caddy handles HTTPS termination and proxies requests to n8n on localhost:5678. n8n is not directly accessible from the network — only via Caddy.

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
ssh root@192.168.0.202 "qm start 107"

# Stop VM
ssh root@192.168.0.202 "qm stop 107"

# Restart VM
ssh root@192.168.0.202 "qm restart 107"

# Check status
ssh root@192.168.0.202 "qm status 107"

# Get IP
ssh root@192.168.0.202 "ip neigh | grep bc:24:11:3b:86:22"
```

## Notes
- n8n is installed directly via npm (no Docker)
- Runs as a systemd service for auto-start on boot
- Basic auth is enabled with default credentials (admin/admin)
- SQLite is used for the database (default n8n setup)
- Python task runner is not configured (JS task runner is active)
- HTTPS is configured via Caddy reverse proxy with self-signed TLS
- n8n binds to localhost only (127.0.0.1:5678) — external access only through Caddy on 443

## To Do
- [ ] Change default admin credentials
- [ ] Configure n8n for production use (webhook URL, etc.)
- [ ] Set up automated backups
- [x] HTTPS/TLS configured via Caddy
- [ ] Configure external task runner if needed
- [ ] Consider using a real domain + Let's Encrypt certificate for trusted TLS
