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

### Cluster Services Index (port 8092 / HTTPS 443)

A self-hosted index page that lists all services running on the cluster, with links to accessible ones.

- **HTTP URL**: `http://dertog:8092`
- **HTTPS URL**: `https://dertog.tailb4b58.ts.net/` (Tailscale, port 443)
- **Server**: Python static server
- **Systemd unit**: `cluster-services.service` (user unit)
- **Tailscale serve**: `tailscale-serve-cluster.service` (system unit, exposes 8092 on HTTPS/443)
- **Files**: `~/cluster-services/index.html`, `~/cluster-services-serve.py`
- **Purpose**: Single entry point to discover all cluster services

```bash
# Check status
systemctl --user status cluster-services
sudo systemctl status tailscale-serve-cluster

# Restart
systemctl --user restart cluster-services
sudo systemctl restart tailscale-serve-cluster
```

### clip-together Frontend (port 8091)

Static SPA serving the clip-together React/Vite frontend, built elsewhere (homestar-runner) and deployed via rsync.

- **URL**: `http://dertog:8091`
- **Server**: Python static SPA server with `index.html` fallback
- **Systemd unit**: `clip-together-web.service` (user unit)
- **Deploy source**: `~/clip-together-web/` (rsync'd from homestar-runner)
- **Build host**: `homestar-runner` (192.168.0.154) via GitHub Actions
- **API backend**: `sb-edge` (192.168.0.137:8001) with CORS enabled

```bash
# Check status
systemctl --user status clip-together-web

# Restart after manual deploy
systemctl --user restart clip-together-web
```

### Seykhl Health Dashboard (port 8093)

Live cluster health and performance metrics fetched from the Proxmox host via SSH.

- **URL**: `http://dertog:8093`
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

### Performance Dashboard (port 8080)

- **URL**: `http://dertog:8080`
- **Process**: `/opt/perf-dashboard/dashboard_server.py` (root)
- **Purpose**: System performance monitoring dashboard

## Current Status
- **SSH**: ✅ `ssh stephen@192.168.0.138` works with key auth
- **Sudo**: ✅ Passwordless sudo configured
- **Memory**: Ballooning enabled (2GB current, up to 6GB max)
- **Disk**: 30GB total, 28GB free
- **cluster-services**: ✅ Active on port 8092
- **seykhl-health**: ✅ Active on port 8093
- **clip-together-web**: ✅ Active on port 8091
- **perf-dashboard**: ✅ Active on port 8080

## Deploy Files on dertog

- `~/cluster-services/index.html` — Cluster services index page (version-controlled)
- `~/cluster-services-serve.py` — Python static server for cluster-services
- `~/.config/systemd/user/cluster-services.service` — systemd user unit
- `~/seykhl-health.py` — Seykhl health dashboard server (version-controlled)
- `~/.config/systemd/user/seykhl-health.service` — systemd user unit
- `~/clip-together-web/` — Static SPA files (index.html, assets/)
- `~/clip-together-serve.py` — Python static server with SPA fallback
- `~/.config/systemd/user/clip-together-web.service` — systemd user unit

## Notes
- CPU type `host` for modern tool compatibility
- Ballooning enabled for memory efficiency
- `qemu-guest-agent` not available in default Debian 13 repos (not critical for basic operation)
- **Do not install node/npm** on dertog — the frontend is built on homestar-runner and copied as static files
- To change `VITE_*` env vars, the frontend must be **rebuilt** (env vars are baked into the bundle at build time)
