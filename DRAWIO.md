# drawio — Self-hosted drawio (diagrams.net)

**Last verified:** 2026-09-05. Container `drawio` (`jgraph/drawio`) and
cloudflared are active; local port 8080 and public HTTPS return 200. The VM
remains on Sefer `vmbr0` at `192.168.0.149`. The configured nightly VM backup is not a clean success: September 5 archive transfer completed but NAS pruning failed. See [BACKUPS.md](BACKUPS.md).

## Overview
`drawio` (VMID 114) is a lightweight VM running the official
[jgraph/drawio](https://hub.docker.com/r/jgraph/drawio) Docker image — a fully
self-hosted instance of the drawio / diagrams.net editor. Diagrams never leave
the LAN (no external service calls required for editing).

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 114 |
| **Name** | drawio |
| **OS** | Debian 13 "Trixie" |
| **CPU** | host |
| **Cores** | 1 |
| **Memory** | 2GB |
| **Disk** | 20GB (`vmdata`, scsi0) |
| **Network** | vmbr0 (static IP via cloud-init), virtio |
| **MAC** | BC:24:11:1A:97:34 |
| **LAN IP** | 192.168.0.149 |
| **mDNS** | `drawio.local` (avahi-daemon) |
| **Created** | 2026-07-28 |
| **Status** | Running |
| **Cloud-Init** | Enabled (user: stephen) |

## Access

### Web Interface (Public)
- **URL:** https://drawio.meshcrawler.com
- **TLS:** Cloudflare (via Cloudflare Tunnel)
- **Access:** Public

### Web Interface (LAN)
- **URL:** http://drawio.local:8080 or http://192.168.0.149:8080
- **Access:** LAN only

### SSH
```bash
ssh drawio            # alias in ~/.ssh/config
ssh stephen@192.168.0.149
```

## Services

| Service | Port | Type | Description |
|---------|------|------|-------------|
| drawio (Docker) | 8080 | Web App | drawio editor (container name `drawio`, restart policy `unless-stopped`) |
| cloudflared | — | Tunnel | Cloudflare Tunnel for public access (`drawio.meshcrawler.com`) |

## Cloudflare Tunnel

| Field | Value |
|-------|-------|
| **Tunnel name** | drawio |
| **Tunnel ID** | `c3f26824-34cf-4c8d-9bdc-8c0f243619ee` |
| **Config** | `/etc/cloudflared/config.yml` |
| **Credentials** | `/etc/cloudflared/c3f26824-34cf-4c8d-9bdc-8c0f243619ee.json` |
| **Public URL** | https://drawio.meshcrawler.com |
| **Proxied service** | `http://localhost:8080` |
| **TLS** | Cloudflare-managed |

### Config File
```yaml
tunnel: c3f26824-34cf-4c8d-9bdc-8c0f243619ee
credentials-file: /etc/cloudflared/c3f26824-34cf-4c8d-9bdc-8c0f243619ee.json

ingress:
  - hostname: drawio.meshcrawler.com
    service: http://localhost:8080
  - service: http_status:404
```

### Management
```bash
ssh drawio "sudo systemctl status cloudflared"
ssh drawio "sudo journalctl -u cloudflared -f"
```

(An earlier tunnel named `drawio` — `936f9974-...` from 2026-07-28 — had no
connectors and unrecoverable credentials; it was deleted and recreated as
`c3f26824-...` on 2026-08-02.)

## Management

```bash
# Container status / logs
ssh drawio "docker ps"
ssh drawio "docker logs -f drawio"

# Restart
ssh drawio "sudo docker restart drawio"

# Upgrade to latest drawio
ssh drawio "sudo docker pull jgraph/drawio && sudo docker stop drawio && \
  sudo docker rm drawio && sudo docker run -d --name drawio \
  --restart unless-stopped -p 8080:8080 jgraph/drawio"
```

## Notes

- Essentially idle when not in use (load ~0.01); 2GB is ample.
- QEMU guest agent is enabled in the Proxmox config (`agent: enabled=1`) but
  `qemu-guest-agent` is not installed/running in the guest — install it from
  the guest (`sudo apt-get install qemu-guest-agent`) if you want
  `qm guest exec` / IP reporting from the Proxmox UI.
- The drawio container was initially deployed 2026-07-28; no data volume is
  mounted — diagrams live in the browser session unless the user saves
  (download / device storage). Add a volume mount if server-side diagram
  storage is ever wanted.
- The VM now runs on `sefer` (`192.168.0.100`) and is included in the nightly
  `sefer-light-services` Proxmox backup job.
