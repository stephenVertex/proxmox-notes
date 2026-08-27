# docuseal — DocuSeal Document Signing Platform

## Overview
`docuseal` (VMID 113) is a lightweight VM running [DocuSeal](https://github.com/docusealco/docuseal), an open-source platform for secure digital document signing and processing. Create PDF forms, have them filled and signed online on any device.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 113 |
| **Name** | docuseal |
| **OS** | Debian 13 "Trixie" |
| **CPU** | host |
| **Cores** | 1 |
| **Memory** | 2GB |
| **Disk** | 20GB (`vmdata`, scsi0) |
| **Network** | vmbr0 (static IP), virtio |
| **MAC** | BC:24:11:7A:9E:42 |
| **LAN IP** | 192.168.0.139 |
| **Tailscale IP** | 100.117.77.67 |
| **Status** | Running |
| **Cloud-Init** | Enabled (user: stephen) |

## Access

### Web Interface (Public)
- **URL:** https://docuseal.meshcrawler.com
- **TLS:** Cloudflare (via Cloudflare Tunnel)
- **Access:** Public — anyone with the link can sign documents

### Web Interface (Tailscale)
- **URL:** https://docuseal.tailb4b58.ts.net
- **Access:** Tailnet only

### Web Interface (LAN)
- **URL:** http://192.168.0.139:3000
- **Access:** LAN only

### SSH
```bash
ssh stephen@192.168.0.139
# or via Tailscale
ssh stephen@100.117.77.67
# or via hostname (add to /etc/hosts: 192.168.0.139 docuseal)
ssh stephen@docuseal
```

## Network Details
- **LAN IP:** 192.168.0.139 (static via cloud-init)
- **Gateway:** 192.168.0.1
- **Tailscale IP:** 100.117.77.67
- **Tailscale Hostname:** docuseal
- **Bridge:** vmbr0

## Services

| Service | Port | Type | Description |
|---------|------|------|-------------|
| DocuSeal (Docker) | 3000 | Web App | DocuSeal web interface + API |
| Tailscale Serve | 443 | HTTPS Proxy | Tailscale-managed HTTPS within tailnet |
| cloudflared | — | Tunnel | Cloudflare Tunnel for public access |

## Docker Configuration

### Container
```bash
docker run -d \
  --name docuseal \
  --restart unless-stopped \
  -p 3000:3000 \
  -v /opt/docuseal/data:/data \
  docuseal/docuseal:latest
```

### Data
- **Data directory:** `/opt/docuseal/data`
- **Database:** SQLite (default, stored in data volume)
- **File storage:** Local disk (stored in data volume)

### Management
```bash
# Check container status
sudo docker ps

# View logs
sudo docker logs -f docuseal

# Restart container
sudo docker restart docuseal

# Update DocuSeal
sudo docker pull docuseal/docuseal:latest
sudo docker stop docuseal
sudo docker rm docuseal
sudo docker run -d --name docuseal --restart unless-stopped \
  -p 3000:3000 -v /opt/docuseal/data:/data docuseal/docuseal:latest
```

## Cloudflare Tunnel

| Field | Value |
|-------|-------|
| **Tunnel name** | docuseal |
| **Tunnel ID** | `fdbd66cf-8ea3-4f25-8ea8-440997b14378` |
| **Config** | `/etc/cloudflared/config.yml` |
| **Credentials** | `/etc/cloudflared/fdbd66cf-8ea3-4f25-8ea8-440997b14378.json` |
| **Public URL** | https://docuseal.meshcrawler.com |
| **Proxied service** | `http://localhost:3000` |
| **TLS** | Cloudflare-managed |

### Config File
```yaml
tunnel: fdbd66cf-8ea3-4f25-8ea8-440997b14378
credentials-file: /etc/cloudflared/fdbd66cf-8ea3-4f25-8ea8-440997b14378.json

ingress:
  - hostname: docuseal.meshcrawler.com
    service: http://localhost:3000
  - service: http_status:404
```

## Tailscale

- **Installed:** 2026-07-22
- **Tailscale Serve:** Port 3000 (HTTPS within tailnet)
- **Tailscale Funnel:** Not configured (public access via Cloudflare Tunnel instead)

## Systemd Services

| Service | File | Status |
|---------|------|--------|
| **docker** | `/usr/lib/systemd/system/docker.service` | Enabled, Active |
| **cloudflared** | `/etc/systemd/system/cloudflared.service` | Enabled, Active |
| **tailscaled** | `/usr/lib/systemd/system/tailscaled.service` | Enabled, Active |
| **tailscale-serve** | `/etc/systemd/system/tailscale-serve.service` | Enabled |

## Verification Commands
```bash
# Check Docker
sudo docker ps

# Check cloudflared
sudo systemctl status cloudflared

# Check Tailscale
sudo tailscale status

# Test web interface
curl -sL -o /dev/null -w '%{http_code}' https://docuseal.meshcrawler.com

# Test LAN
curl -sL -o /dev/null -w '%{http_code}' http://localhost:3000
```

## Resource Usage
- **CPU:** 1 vCPU (very light usage)
- **RAM:** 2GB (Docker + DocuSeal)
- **Disk:** 20GB (OS + Docker image + data)
- **Docker image size:** ~216 MB

## Notes
- DocuSeal uses SQLite by default; can be switched to PostgreSQL by setting `DATABASE_URL` env var
- Data is persisted at `/opt/docuseal/data` — back up this directory
- Container uses `--restart unless-stopped` so it survives reboots
- Cloudflare Tunnel provides public access without port forwarding
- For SMTP (email notifications to signers), configure in DocuSeal admin settings
- The VM now runs on `sefer` (`192.168.0.100`) and is included in the nightly
  `sefer-light-services` Proxmox backup job. At the 2026-08-27 inventory its
  in-guest QEMU agent was not responding, so use SSH or console access rather
  than guest-agent commands until it is repaired.
