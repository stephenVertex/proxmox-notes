# Proxmox Infrastructure Overview

**Document Version:** 2026-08-11
**Proxmox Node:** seykhl (192.168.0.202)
**PVE Version:** 9.1.1

---

## Node Details

- **Hostname:** `seykhl`
- **IP Address:** `192.168.0.202` (LAN), `192.168.1.202` (alternative)
- **MAC Address:** Various (bridge interfaces)
- **OS:** Debian (Proxmox VE)
- **Kernel:** Linux 6.17.2-1-pve
- **Cluster:** Single-node (not part of a cluster)

---

## Virtual Machines

| VMID | Name | Status | RAM | Disk | LAN IP | MAC | Purpose |
|------|------|--------|-----|------|--------|-----|---------|
| 100 | doltsvr | running | 24GB | 64GB | 192.168.0.150 / 100.101.145.38 (TS) | bc:24:11:d0:43:5d | Dolt SQL Server |
| 101 | jeffrey-dev | stopped | 4GB | 20GB | 192.168.0.132 | bc:24:11:cd:26:f7 | Development VM |
| 102 | yesod-postgres-server | running | 6GB | 120GB | 192.168.0.155 / 100.115.10.68 (TS) | bc:24:11:00:88:f5 | PostgreSQL for Yesod |
| 103 | seykhl-actions-runner | running | 4GB | 30GB | 192.168.0.154 | bc:24:11:6c:cf:b7 | GitHub Actions Runner host |
| 104 | dertog | running | 6GB | 30GB | 192.168.0.138 | bc:24:11:90:a9:cc | Dashboard Server |
| 105 | aicoe-social-runner | running | 2GB | 20GB | 192.168.0.147 | bc:24:11:a4:ce:80 | Social Media Monitor |
| 106 | yesod-runner-1 | running | 16GB | 40GB | 192.168.0.152 | bc:24:11:a0:58:60 | Yesod Agent Runner |
| 107 | n8n-server | running | 4GB | 30GB | 192.168.0.145 | bc:24:11:3b:86:22 | n8n Automation |
| 108 | yesod-runner-2 | running | 16GB | 56GB | 192.168.0.148 | bc:24:11:3f:86:eb | Yesod Agent Runner |
| 109 | yesod-runner-base | stopped | 8GB | 20GB | N/A | bc:24:11:b3:bd:df | Yesod Runner Template |
| 110 | yesod-runner-3 | running | 16GB | 60GB | 192.168.0.136 | bc:24:11:68:88:b3 | Yesod Agent Runner |
| 111 | sb-edge | running | 4GB | 20GB | 192.168.0.137 | bc:24:11:5e:d5:a8 | Supabase Edge Runtime |
| 112 | yesod-dispatch | running | 4GB | 64GB | 192.168.0.140 / 100.123.34.77 (TS) | bc:24:11:e3:c0:cf | Yesod Dispatch |
| 113 | docuseal | running | 2GB | 20GB | 192.168.0.139 / 100.117.77.67 (TS) | bc:24:11:7a:9e:42 | DocuSeal Document Signing |
| 114 | drawio | running | 2GB | 20GB | 192.168.0.149 | bc:24:11:1a:97:34 | drawio Diagram Server |
| 116 | bukher | running | 4GB | 30GB | 192.168.0.169 / 100.77.145.88 (TS) | bc:24:11:51:5f:ad | RSS Ingestion (RssHub + Miniflux) |
| 203 | test-full-201 | stopped | 4GB | 33GB | N/A | bc:24:11:67:9c:b6 | Test/Experimental |
| 205 | opensymphony-base | stopped | 4GB | 33GB | N/A | bc:24:11:4a:19:61 | Test/Experimental |

---

## LXC Containers

| CTID | Name | Status | CPU | RAM | Disk | LAN IP | MAC | Purpose |
|------|------|--------|-----|-----|------|--------|-----|---------|
| 115 | dynamodb | running | 1 | 1GB | 8GB | 192.168.0.144 | bc:24:11:a3:ea:0d | Amazon DynamoDB Local (port 8000) |

---

## Network Configuration

- **Bridge:** vmbr0 (bridge to LAN)
- **Network Model:** virtio for all VMs
- **IP Range:** 192.168.0.x/24 (LAN)
- **DHCP:** Enabled (VMs get IPs via DHCP)
- **DNS:** Local DNS entries added to `/etc/hosts` on admin machines

### Known Hostnames

All hostnames are present in both `/etc/hosts` and `~/.ssh/config` on admin machines
(the SSH config pins `HostName` to the IP, so aliases work even without /etc/hosts).
VM 100 was renamed from `dolt-server` to `doltsvr` in Proxmox on 2026-06-09 so all
layers (Proxmox, /etc/hosts, SSH config, guest hostname) use the same name.

**mDNS (2026-08-02):** every cluster node except docuseal now runs
`avahi-daemon` and is reachable as `<hostname>.local` from any Mac/Linux machine
on the LAN — no /etc/hosts entry required. Note VM 106's guest hostname is
`yesod-runner-1`, so it answers as `yesod-runner-1.local` (not `yesod-runner.local`).
docuseal is pending (its sshd is down and the QEMU guest agent isn't running;
avahi needs to be installed from the console).

- `seykhl` → 192.168.0.202 (Proxmox node)
- `yesod-postgres-server` → 192.168.0.155 (Tailscale: 100.115.10.68)
- `yesod-runner` → 192.168.0.152
- `yesod-runner-2` → 192.168.0.148
- `yesod-runner-3` → 192.168.0.136
- `yesod-dispatch` → 192.168.0.140 (Tailscale: 100.123.34.77)
- `sb-edge` → 192.168.0.137 (Tailscale: 100.115.156.68)
- `seykhl-actions-runner` → 192.168.0.154
- `doltsvr` → 192.168.0.150 (Tailscale: 100.101.145.38)
- `dertog` → 192.168.0.138
- `aicoe-social-runner` → 192.168.0.147
- `jeffrey-dev` → 192.168.0.132
- `n8n-server` → 192.168.0.145
- `docuseal` → 192.168.0.139 (Tailscale: 100.117.77.67)
- `drawio` → 192.168.0.149
- `bukher` → 192.168.0.169 (Tailscale: 100.77.145.88; mDNS: `bukher.local`)
- `dynamodb` → 192.168.0.144 (LXC; DynamoDB endpoint on port 8000; resolves via mDNS as `dynamodb.local`, no /etc/hosts entry needed)

---

## Access Methods

### Cluster Services Index
- **HTTP:** http://dertog:8092
- **HTTPS:** https://dertog.tailb4b58.ts.net/ (Tailscale, port 443)
- **Description:** Self-hosted index page listing all services on the cluster with links

### Database Details Dashboard
- **URL:** http://dertog:8094
- **Description:** PostgreSQL and Dolt database sizes, counts, and recent activity

### Proxmox Web UI
- **URL:** https://192.168.0.202:8006
- **Credentials:** Root credentials (stored in password manager)

### SSH to Proxmox Host
```bash
ssh seykhl          # alias in ~/.ssh/config (root@192.168.0.202)
```

### SSH to VMs
All VMs have passwordless SSH via `~/.ssh/id_ed25519`; users and aliases are set
in `~/.ssh/config`, so the hostname alone is enough:
```bash
ssh doltsvr         # or any VM name from the table above
```
User is `stephen` everywhere except `jeffrey-dev`, which only accepts the
`jeffrey` user (root/stephen are refused by a forced-command key).

### Console Access
```bash
# Via Proxmox CLI
ssh root@192.168.0.202 "qm console <vmid>"
```

---

## Storage

- **Primary Storage:** local-lvm (LVM thin pool on NVMe SSD + SATA SSD)
- **Physical Volumes:**
  - `/dev/nvme0n1p3` — 237GB (original NVMe)
  - `/dev/sda` — 512GB Fanxiang S101 SATA SSD (added 2026-06-11)
- **Total LVM Thin Pool:** ~634GB (was ~141GB)
- **Live data utilization:** 66.94% as of 2026-08-10 UTC
- **Physically available in the thin pool:** ~210GB
- **Thin logical allocations:** ~751GB, which exceeds the 634GB pool; monitor
  physical utilization and do not treat thin-provisioned logical capacity as
  free space
- **ISOs:** /var/lib/vz/template/iso/
- **VM Disks:** local-lvm (thin-provisioned)
- **Backups:** Configured on NAS (see individual VM docs)

---

## Documentation Files

| VM | Documentation File |
|------|-------------------|
| doltsvr | [DOLT_SERVER.md](DOLT_SERVER.md) |
| jeffrey-dev | [JEFFREY-DEV.md](JEFFREY-DEV.md) |
| yesod-postgres-server | [YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md) |
| seykhl-actions-runner | [SEYKHL_ACTIONS_RUNNER.md](SEYKHL_ACTIONS_RUNNER.md) |
| dertog | [DERTOG.md](DERTOG.md) |
| aicoe-social-runner | [AICOE_SOCIAL_RUNNER.md](AICOE_SOCIAL_RUNNER.md) |
| yesod-runner | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| yesod-runner-2 | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| yesod-runner-3 | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| sb-edge | [SB_EDGE.md](SB_EDGE.md) |
| n8n-server | [N8N_SERVER.md](N8N_SERVER.md) |
| test-full-201 | [TEST_FULL_201.md](TEST_FULL_201.md) |
| docuseal | [DOCUSEAL.md](DOCUSEAL.md) |
| opensymphony-base | [OPEN_SYMPHONY_BASE.md](OPEN_SYMPHONY_BASE.md) |
| drawio | [DRAWIO.md](DRAWIO.md) |
| dynamodb | [DYNAMODB_LOCAL.md](DYNAMODB_LOCAL.md) |

---

## Resource Summary

- **Total Running VMs:** 14
- **Total Running LXC Containers:** 1
- **Running VM RAM Allocated:** 110GB + 1GB LXC
- **VM Boot Disks Allocated:** 710GB logical + 8GB LXC
- **Stopped VMs:** 4 (jeffrey-dev, test-full-201, opensymphony-base, yesod-runner-base)
- **Stopped VMs RAM:** 20GB
- **Stopped VMs Disk:** 106GB

---

## Quick Commands

```bash
# List all VMs
ssh root@192.168.0.202 "qm list"

# List all containers
ssh root@192.168.0.202 "pct list"

# Check node status
ssh root@192.168.0.202 "pveversion"

# Check VM config
ssh root@192.168.0.202 "cat /etc/pve/nodes/seykhl/qemu-server/<vmid>.conf"

# Start a VM
ssh root@192.168.0.202 "qm start <vmid>"

# Stop a VM
ssh root@192.168.0.202 "qm stop <vmid>"

# Restart a VM
ssh root@192.168.0.202 "qm restart <vmid>"
```

---

## Notes

- All VMs use virtio network interfaces for optimal performance
- Most VMs run headless (no display)
- Cloud-init is used for initial configuration on Debian-based VMs
- SSH keys are installed via cloud-init for passwordless access
- The `yesod-runner` (VM 106) was created from a copy of the yesod-aicoe repo and configured to run the codefactory dispatch service
- `yesod-runner-base` (VM 109) is a template VM with pre-installed software (uv, cargo, opencode, gh) for rapid runner deployment
- `yesod-runner-2` (VM 108) and `yesod-runner-3` (VM 110) are cloned from the template and configured as active runners
- VM 106 IP changed from 192.168.0.146 to 192.168.0.152 after network reservation fix
- `sb-edge` (VM 111) runs a complete Supabase stack (PostgREST + Edge Runtime + nginx) with Tailscale HTTPS access
- `dynamodb` (CTID 115) is the first LXC container on the node (created 2026-08-02); 1 core / 1GB, runs Amazon DynamoDB Local on port 8000 — see [DYNAMODB_LOCAL.md](DYNAMODB_LOCAL.md)
- VM 106 is named `yesod-runner-1` in Proxmox; SSH alias / docs still use `yesod-runner`
- VM 102 disk was expanded to 120GB (observed 2026-08-02)
- VM 112 (`yesod-dispatch`) was expanded online from 20GB to 64GB on
  2026-08-10. The guest's first partition and ext4 root filesystem were grown
  in place without a reboot; the post-growth snapshot had about 45GB free.
  This is interim Conductor headroom while the larger replacement host is
  forthcoming, not a reason to add application services directly to `seykhl`.

---

## To Do

- [x] Set up Tailscale on doltsvr (100.101.145.38) — joined 2026-06-16
- [x] Set up Tailscale on yesod-postgres-server (100.115.10.68) — joined
- [ ] Set up Tailscale on remaining VMs for secure remote access
- [ ] Configure automated backups for all VMs
- [ ] Document test VMs (203, 205) if they are needed for production
- [ ] Create monitoring dashboard for VM resource usage
- [ ] Add firewall rules for VM network isolation
- [x] Install 512GB SATA drive (added 2026-06-11) — expanded LVM thin pool to ~634GB
- [ ] Create runner self-update mechanism (system packages, uv, cargo, opencode)
