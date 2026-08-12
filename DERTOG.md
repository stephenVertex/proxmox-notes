# Dertog — Debian 13 Dashboard Server

## Overview
`dertog` (VMID 104) is a Debian 13 VM on Proxmox host `seykhl`. Named after the Yiddish *"der tog"* (the day/newspaper), it's a platform for hosting various dashboards and distilled data visualizations.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 104 |
| **Name** | dertog |
| **OS** | Debian 13 "Trixie" (latest stable) |
| **CPU** | host (AVX passthrough) |
| **Cores** | 2 |
| **Memory** | 6GB (with ballooning) |
| **Disk** | 30GB (raw on local-lvm) |
| **Network** | vmbr0 (bridge to LAN) |
| **Net Model** | virtio |
| **Display** | none (headless server) |

## Network Details
- **MAC Address**: BC:24:11:90:A9:CC
- **LAN IP**: 192.168.0.138 (DHCP)
- **Hostname**: dertog
- **DNS**: Will be added to local `/etc/hosts` on admin machines

## Purpose
- Host dashboards at various ports
- Receive distilled data uploads from workstation
- Serve as a central visualization hub
- Serve the **clip-together** React/Vite frontend as a static SPA (port 8091)

## SSH Access
```bash
ssh stephen@dertog
```
Passwordless SSH via offline disk mount technique (see SSH_ENABLE_HOWTO.md).

## Resources
- Proxmox Host: `seykhl` (192.168.0.202)
- Cloud Image: `/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2`
- VM Disk: `local-lvm:vm-104-disk-0`

## Build Log

### Creation (2026-05-18)
1. Created VM 104 on Proxmox with Debian 13 cloud image
2. Configured cloud-init with user `stephen`
3. Enabled memory ballooning (6GB max, 2GB min)
4. Started VM and got IP `192.168.0.138`

### SSH Key Injection (Offline Disk Mount)
Following SSH_ENABLE_HOWTO.md technique:
```bash
# Stop VM
qm stop 104

# Mount root partition
losetup -f --show --offset=134217728 /dev/pve/vm-104-disk-0
mount /dev/loop0 /mnt/vm104

# Inject SSH key
mkdir -p /mnt/vm104/home/stephen/.ssh
chmod 700 /mnt/vm104/home/stephen/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBoBSMwr4DtS0F8gzJPJCm0CMZIhvpsyamSfyHAX/A+S stephen.barr@devfactory.com" > /mnt/vm104/home/stephen/.ssh/authorized_keys
chmod 600 /mnt/vm104/home/stephen/.ssh/authorized_keys
chown -R 1000:1000 /mnt/vm104/home/stephen/.ssh

# Fix empty SSH host keys (cloud-init first-boot issue)
rm -f /mnt/vm104/etc/ssh/ssh_host_*
ssh-keygen -A -f /mnt/vm104

# Add passwordless sudo
echo "stephen ALL=(ALL) NOPASSWD: ALL" > /mnt/vm104/etc/sudoers.d/stephen
chmod 440 /mnt/vm104/etc/sudoers.d/stephen

# Unmount and restart
umount /mnt/vm104
losetup -d /dev/loop0
qm start 104
```

### Post-Create Fixes
- **Issue**: SSH host keys were 0-byte files (cloud-init first-boot race condition)
- **Symptom**: `sshd: no hostkeys available -- exiting.`
- **Fix**: Regenerated host keys with `ssh-keygen -A` while disk was mounted offline

- **Issue**: Passwordless sudo not configured for `stephen` user
- **Fix**: Added `/etc/sudoers.d/stephen` via offline disk mount

## Services

### HTTPS Routing (Tailscale + nginx)

All services are available over HTTPS via Tailscale, routed through nginx on port 8088.

**Architecture:** Tailscale TLS (443) → nginx (8088, prefix-stripping proxy) → backend apps

| HTTPS path | Proxies to | Prefix stripped | Backend |
|------------|-----------|-----------------|---------|
| `/` | `127.0.0.1:8092` | — | Cluster services index |
| `/yesod/` | `127.0.0.1:8090` | `/yesod` | Yesod API server (natively prefix-aware, see below) |
| `/yesod/ws` | `127.0.0.1:8765` | — | Yesod live-viz WebSocket (wss, avoids mixed content) |
| `/viz/*` | 301 → `/yesod/viz/*` | — | Legacy absolute viz paths |
| `/clip/` | `127.0.0.1:8091` | `/clip` | clip-together frontend |
| `/health/` | `127.0.0.1:8093` | `/health` | Seykhl health dashboard |
| `/db/` | `127.0.0.1:8094` | `/db` | Database details |
| `/sjbis/` | `127.0.0.1:7878` | `/sjbis` | SJBIS dashboard |
| `/perf/` | `127.0.0.1:8080` | `/perf` | Performance dashboard |
| `/sjbgtd/`, `/api/`, `/ws` | `127.0.0.1:8766/8767` | varies | sjbgtd DAG visualizer (owns root `/api/` and `/ws`!) |

- **nginx config**: `/etc/nginx/sites-enabled/dertog-router` — a REAL FILE, not a symlink;
  `sites-available/dertog-router` is kept in sync manually. Edit sites-enabled (or both).
- **Tailscale serve**: `tailscale serve --bg 8088` (background, port 443)
- **Old `tailscale-serve-cluster.service`**: Removed (was foreground, only proxied 8092)

**Yesod /yesod/ prefix handling (2026-07-25, ys-yes-j9fu):** serve.py natively honors
`X-Forwarded-Prefix` — it rewrites its own `href/src/action/fetch/EventSource` output and
`live-viz/config.js` (API base, `ws://host:8765` → `wss://host/yesod/ws` under https), so
nginx just forwards the prefix/proto, no `sub_filter` needed. The 2026-07-23 interim
`sub_filter` rewrite block was retired the same day the fix deployed (double-prefixing
`/yesod/yesod/...` was the tell that both nginx and serve.py were rewriting). `absolute_redirect
off` still keeps redirects relative. The cluster-services index page shows an HTTPS link for
every proxied service.

**sjbgtd `/sjbgtd/` prefix stripping (2026-08-12):** The live nginx route must use
`proxy_pass http://127.0.0.1:8766/;` with the trailing slash. Without it, nginx forwards
`/sjbgtd/sidecar/viewer/` unchanged to `sidecar.template_api_server`, which expects
`/sidecar/viewer/` and returns 404. The live config at
`/etc/nginx/sites-enabled/dertog-router` was corrected, validated with `nginx -t`, and
reloaded. The backup is `/etc/nginx/sites-enabled/dertog-router.bak-20260812-sidecar`.

**Direct HTTP access is unchanged** — all ports (8090, 8091, 8092, 8093, 8094, 7878, 8080) still work as before.

```bash
# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check tailscale serve
sudo tailscale serve status

# Reload nginx after config change
sudo nginx -t && sudo systemctl reload nginx
```

### Cluster Services Index (port 8092 / HTTPS /)

A self-hosted index page that lists all services running on the cluster, with links to accessible ones.

- **HTTP URL**: `http://dertog:8092`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/` (via nginx → 8092)
- **Server**: Python static server
- **Systemd unit**: `cluster-services.service` (user unit)
- **Files**: `~/cluster-services/index.html`, `~/cluster-services-serve.py`
- **Purpose**: Single entry point to discover all cluster services

```bash
# Check status
systemctl --user status cluster-services

# Restart
systemctl --user restart cluster-services
```

### Yesod API Server (port 8090 / HTTPS /yesod/)

- **HTTP URL**: `http://dertog:8090`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/yesod/`
- **Process**: `yesod` binary (port 8090)
- **Purpose**: HTTP API + site for Yesod platform

### clip-together Frontend (port 8091 / HTTPS /clip/)

Static SPA serving the clip-together React/Vite frontend, built on `seykhl-actions-runner` and deployed via rsync.

- **HTTP URL**: `http://dertog:8091`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/clip/` (via nginx → 8091)
- **Server**: Python static SPA server with `index.html` fallback
- **Systemd unit**: `clip-together-web.service` (user unit)
- **Deploy source**: `~/clip-together-web/` (rsync'd from `seykhl-actions-runner`)
- **Build host**: `seykhl-actions-runner` (192.168.0.154) via GitHub Actions label `dertog-deploy`
- **API backend**: `sb-edge` (192.168.0.137:8001) with CORS enabled

```bash
# Check status
systemctl --user status clip-together-web

# Restart after manual deploy
systemctl --user restart clip-together-web
```

### Seykhl Health Dashboard (port 8093 / HTTPS /health/)

Live cluster health and performance metrics fetched from the Proxmox host via SSH.

- **HTTP URL**: `http://dertog:8093`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/health/` (via nginx → 8093)
- **Server**: Python dynamic server (fetches live data from seykhl)
- **Systemd unit**: `seykhl-health.service` (user unit)
- **File**: `~/seykhl-health.py`
- **Features**: Node status, load/memory, storage, VM summary, auto-refresh (30s)
- **Data source**: `pvesh` commands via SSH to root@seykhl

```bash
# Check status
systemctl --user status seykhl-health

# Restart
systemctl --user restart seykhl-health
```

### Database Details (port 8094 / HTTPS /db/)

Database details dashboard for PostgreSQL (yesod-postgres-server) and Dolt (doltsvr).

- **HTTP URL**: `http://dertog:8094`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/db/` (via nginx → 8094)
- **Server**: Python dynamic server
- **Systemd unit**: `db-details.service` (user unit)
- **File**: `~/db-details.py` (version-controlled)
- **Features**:
  - PostgreSQL: database list, sizes, recent activity (commits/inserts/updates/deletes), active connections
  - Dolt: database list, table counts, recent commits
- **Credentials**: Read from existing `~/.config/yesod/database.toml` and `~/.config/yesod/dolt.toml`

```bash
# Check status
systemctl --user status db-details

# Restart
systemctl --user restart db-details
```

### SJBIS (port 7878 / HTTPS /sjbis/)

- **HTTP URL**: `http://dertog:7878`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/sjbis/` (via nginx → 7878)
- **Process**: `/home/stephen/sjbis/sjbis daemon start --port 7878`
- **Purpose**: Information surfacer dashboard

### Performance Dashboard (port 8080 / HTTPS /perf/)

- **HTTP URL**: `http://dertog:8080`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/perf/` (via nginx → 8080)
- **Process**: `/opt/perf-dashboard/dashboard_server.py` (root)
- **Purpose**: System performance monitoring dashboard

## Current Status
- **SSH**: ✅ `ssh stephen@192.168.0.138` works with key auth
- **Sudo**: ✅ Passwordless sudo configured
- **Memory**: Ballooning enabled (2GB current, up to 6GB max)
- **Disk**: 30GB total, 28GB free
- **nginx**: ✅ Active on port 8088 (reverse proxy for HTTPS routing)
- **tailscale serve**: ✅ Background, 443 → 8088
- **cluster-services**: ✅ Active on port 8092
- **yesod**: ✅ Active on port 8090
- **seykhl-health**: ✅ Active on port 8093
- **db-details**: ✅ Active on port 8094
- **clip-together-web**: ✅ Active on port 8091
- **sjbis**: ✅ Active on port 7878
- **perf-dashboard**: ✅ Active on port 8080

## Deploy Files on dertog

- `~/cluster-services/index.html` — Cluster services index page (version-controlled)
- `~/cluster-services-serve.py` — Python static server for cluster-services
- `~/.config/systemd/user/cluster-services.service` — systemd user unit
- `~/seykhl-health.py` — Seykhl health dashboard server (version-controlled)
- `~/.config/systemd/user/seykhl-health.service` — systemd user unit
- `~/db-details.py` — Database details dashboard server (version-controlled)
- `~/.config/systemd/user/db-details.service` — systemd user unit
- `~/clip-together-web/` — Static SPA files (index.html, assets/)
- `~/clip-together-serve.py` — Python static server with SPA fallback
- `~/.config/systemd/user/clip-together-web.service` — systemd user unit
- `/etc/nginx/sites-available/dertog-router` — nginx reverse proxy config (HTTPS routing)

## Notes
- CPU type `host` for modern tool compatibility
- Ballooning enabled for memory efficiency
- `qemu-guest-agent` not available in default Debian 13 repos (not critical for basic operation)
- **Do not install node/npm** on dertog — the frontend is built on `seykhl-actions-runner` and copied as static files
- **HTTPS routing**: nginx strips path prefixes via `proxy_pass` trailing-slash syntax. Direct HTTP access to all ports is unchanged.
- To change `VITE_*` env vars, the frontend must be **rebuilt** (env vars are baked into the bundle at build time)
