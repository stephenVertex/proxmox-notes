# Proxmox Infrastructure Overview

**Document Version:** 2026-06-09
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
| 101 | jeffrey-dev | running | 4GB | 20GB | 192.168.0.132 | bc:24:11:cd:26:f7 | Development VM |
| 102 | yesod-postgres-server | running | 6GB | 30GB | 192.168.0.155 | bc:24:11:00:88:f5 | PostgreSQL for Yesod |
| 103 | homestar-runner | running | 4GB | 30GB | 192.168.0.154 | bc:24:11:6c:cf:b7 | GitHub Actions Runner |
| 104 | dertog | running | 6GB | 30GB | 192.168.0.138 | bc:24:11:90:a9:cc | Dashboard Server |
| 105 | aicoe-social-runner | running | 2GB | 20GB | 192.168.0.147 | bc:24:11:a4:ce:80 | Social Media Monitor |
| 106 | yesod-runner | running | 8GB | 20GB | 192.168.0.152 | bc:24:11:a0:58:60 | Yesod Agent Runner |
| 107 | n8n-server | running | 4GB | 30GB | 192.168.0.145 | bc:24:11:3b:86:22 | n8n Automation |
| 108 | yesod-runner-2 | running | 8GB | 20GB | 192.168.0.148 | bc:24:11:3f:86:eb | Yesod Agent Runner |
| 109 | yesod-runner-base | stopped | 8GB | 20GB | N/A | bc:24:11:b3:bd:df | Yesod Runner Template |
| 110 | yesod-runner-3 | running | 8GB | 20GB | 192.168.0.136 | bc:24:11:68:88:b3 | Yesod Agent Runner |
| 111 | sb-edge | running | 4GB | 20GB | 192.168.0.137 | bc:24:11:5e:d5:a8 | Supabase Edge Runtime |
| 203 | test-full-201 | stopped | 4GB | 33GB | N/A | bc:24:11:67:9c:b6 | Test/Experimental |
| 205 | opensymphony-base | stopped | 4GB | 33GB | N/A | bc:24:11:4a:19:61 | Test/Experimental |

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

- `seykhl` → 192.168.0.202 (Proxmox node)
- `yesod-postgres-server` → 192.168.0.155
- `yesod-runner` → 192.168.0.152
- `yesod-runner-2` → 192.168.0.148
- `yesod-runner-3` → 192.168.0.136
- `sb-edge` → 192.168.0.137 (Tailscale: 100.115.156.68)
- `homestar-runner` → 192.168.0.154
- `doltsvr` → 192.168.0.150 (Tailscale: 100.101.145.38)
- `dertog` → 192.168.0.138
- `aicoe-social-runner` → 192.168.0.147
- `jeffrey-dev` → 192.168.0.132
- `n8n-server` → 192.168.0.145

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
- **Used:** ~108GB (16.3%)
- **Available:** ~556GB
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
| homestar-runner | [HOMESTAR_RUNNER.md](HOMESTAR_RUNNER.md) |
| dertog | [DERTOG.md](DERTOG.md) |
| aicoe-social-runner | [AICOE_SOCIAL_RUNNER.md](AICOE_SOCIAL_RUNNER.md) |
| yesod-runner | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| yesod-runner-2 | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| yesod-runner-3 | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| sb-edge | [SB_EDGE.md](SB_EDGE.md) |
| n8n-server | [N8N_SERVER.md](N8N_SERVER.md) |
| test-full-201 | [TEST_FULL_201.md](TEST_FULL_201.md) |
| opensymphony-base | [OPEN_SYMPHONY_BASE.md](OPEN_SYMPHONY_BASE.md) |

---

## Resource Summary

- **Total Running VMs:** 11
- **Total RAM Allocated:** 78GB (24+4+6+4+6+2+8+4+8+8+4)
- **Total Disk Allocated:** ~340GB
- **Stopped VMs:** 3 (test-full-201, opensymphony-base, yesod-runner-base)
- **Stopped VMs RAM:** 16GB
- **Stopped VMs Disk:** ~86GB

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

---

## To Do

- [x] Set up Tailscale on doltsvr (100.101.145.38) — joined 2026-06-16
- [ ] Set up Tailscale on remaining VMs for secure remote access
- [ ] Configure automated backups for all VMs
- [ ] Document test VMs (203, 205) if they are needed for production
- [ ] Create monitoring dashboard for VM resource usage
- [ ] Add firewall rules for VM network isolation
- [x] Install 512GB SATA drive (added 2026-06-11) — expanded LVM thin pool to ~634GB
- [ ] Create runner self-update mechanism (system packages, uv, cargo, opencode)

