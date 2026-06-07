# Proxmox Infrastructure Overview

**Document Version:** 2026-06-05
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
| 100 | dolt-server | running | 24GB | 64GB | 192.168.0.150 | bc:24:11:d0:43:5d | Dolt SQL Server |
| 101 | jeffrey-dev | running | 4GB | 20GB | 192.168.0.132 | bc:24:11:cd:26:f7 | Development VM |
| 102 | yesod-postgres-server | running | 6GB | 30GB | 192.168.0.155 | bc:24:11:00:88:f5 | PostgreSQL for Yesod |
| 103 | homestar-runner | running | 4GB | 30GB | 192.168.0.154 | bc:24:11:6c:cf:b7 | GitHub Actions Runner |
| 104 | dertog | running | 6GB | 30GB | 192.168.0.138 | bc:24:11:90:a9:cc | Dashboard Server |
| 105 | aicoe-social-runner | running | 2GB | 20GB | 192.168.0.147 | bc:24:11:a4:ce:80 | Social Media Monitor |
| 106 | yesod-runner | running | 8GB | 20GB | 192.168.0.146 | bc:24:11:a0:58:60 | Yesod Agent Runner |
| 107 | n8n-server | running | 4GB | 30GB | 192.168.0.145 | bc:24:11:3b:86:22 | n8n Automation |
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
- `seykhl` → 192.168.0.202 (Proxmox node)
- `yesod-postgres-server` → 192.168.0.155
- `yesod-runner` → 192.168.0.146
- `homestar-runner` → 192.168.0.154
- `dolt-server` / `doltsvr` → 192.168.0.150
- `dertog` → 192.168.0.138
- `aicoe-social-runner` → 192.168.0.147
- `jeffrey-dev` → 192.168.0.132
- `n8n-server` → 192.168.0.145

---

## Access Methods

### Proxmox Web UI
- **URL:** https://192.168.0.202:8006
- **Credentials:** Root credentials (stored in password manager)

### SSH to Proxmox Host
```bash
ssh root@192.168.0.202
```

### SSH to VMs
Most VMs have passwordless SSH configured for the `stephen` user:
```bash
ssh stephen@192.168.0.<vm-ip>
```

### Console Access
```bash
# Via Proxmox CLI
ssh root@192.168.0.202 "qm console <vmid>"
```

---

## Storage

- **Primary Storage:** local-lvm (LVM thin pool on local SSD)
- **ISOs:** /var/lib/vz/template/iso/
- **VM Disks:** local-lvm (thin-provisioned)
- **Backups:** Configured on NAS (see individual VM docs)

---

## Documentation Files

| VM | Documentation File |
|------|-------------------|
| dolt-server | [DOLT_SERVER.md](DOLT_SERVER.md) |
| jeffrey-dev | [JEFFREY-DEV.md](JEFFREY-DEV.md) |
| yesod-postgres-server | [YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md) |
| homestar-runner | [HOMESTAR_RUNNER.md](HOMESTAR_RUNNER.md) |
| dertog | [DERTOG.md](DERTOG.md) |
| aicoe-social-runner | [AICOE_SOCIAL_RUNNER.md](AICOE_SOCIAL_RUNNER.md) |
| yesod-runner | [YESOD-RUNNER.md](YESOD-RUNNER.md) |
| n8n-server | [N8N_SERVER.md](N8N_SERVER.md) |
| test-full-201 | [TEST_FULL_201.md](TEST_FULL_201.md) |
| opensymphony-base | [OPEN_SYMPHONY_BASE.md](OPEN_SYMPHONY_BASE.md) |

---

## Resource Summary

- **Total Running VMs:** 8
- **Total RAM Allocated:** 58GB (24+4+6+4+6+2+8+4)
- **Total Disk Allocated:** ~260GB
- **Stopped VMs:** 2 (test-full-201, opensymphony-base)
- **Stopped VMs RAM:** 8GB
- **Stopped VMs Disk:** ~66GB

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

---

## To Do

- [ ] Set up Tailscale on all VMs for secure remote access
- [ ] Configure automated backups for all VMs
- [ ] Document test VMs (203, 205) if they are needed for production
- [ ] Create monitoring dashboard for VM resource usage
- [ ] Add firewall rules for VM network isolation

