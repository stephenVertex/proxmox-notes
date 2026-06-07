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

### n8n Web Interface
- **URL:** http://192.168.0.145:5678
- **Basic Auth:** admin / admin
- **Note:** The default credentials are set in the systemd service. Change these for production use.

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
- **Port:** 5678
- **Process:** Node.js (n8n)
- **Data Directory:** /home/stephen/.n8n
- **Logs:** `sudo journalctl -u n8n -f`

## Maintenance
```bash
# Check service status
ssh stephen@192.168.0.145 "sudo systemctl status n8n"

# Restart n8n
ssh stephen@192.168.0.145 "sudo systemctl restart n8n"

# View logs
ssh stephen@192.168.0.145 "sudo journalctl -u n8n -f"

# Update n8n
ssh stephen@192.168.0.145 "sudo npm install -g n8n && sudo systemctl restart n8n"

# Check n8n version
ssh stephen@192.168.0.145 "n8n --version"
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

## To Do
- [ ] Change default admin credentials
- [ ] Configure n8n for production use (webhook URL, etc.)
- [ ] Set up automated backups
- [ ] Consider adding HTTPS/TLS
- [ ] Configure external task runner if needed
