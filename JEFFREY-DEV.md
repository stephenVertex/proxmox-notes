# jeffrey-dev — Development VM

## Overview
`jeffrey-dev` (VMID 101) is a Debian 13 VM on Proxmox host `seykhl`. It is a general-purpose development environment.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 101 |
| **Name** | jeffrey-dev |
| **OS** | Debian 13 "Trixie" (cloud image) |
| **CPU** | host |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 20GB (local-lvm, scsi0) |
| **Network** | vmbr0 (DHCP), virtio |
| **MAC** | BC:24:11:CD:26:F7 |
| **LAN IP** | 192.168.0.132 |
| **Hostname** | jeffrey-dev |
| **Status** | Running |

## Access

### SSH
The VM is configured with cloud-init but may not have the same SSH key as other VMs. Access via:

```bash
# Via Proxmox console
ssh root@192.168.0.202 "qm console 101"

# Or try SSH directly
ssh stephen@192.168.0.132
```

## Network Details
- **LAN IP:** 192.168.0.132 (DHCP)
- **MAC:** BC:24:11:CD:26:F7
- **Bridge:** vmbr0
- **DNS:** May need to be added to `/etc/hosts` on admin machines

## Purpose
- General-purpose development environment
- Can be used for testing, experimentation, or specific development tasks

## Notes
- Created from Debian 13 cloud image
- Uses cloud-init for initial configuration
- Standard Debian 13 installation with basic tools
- No specific application stack configured (general purpose)

## Maintenance
```bash
# Access via Proxmox console
ssh root@192.168.0.202 "qm console 101"

# Restart VM
ssh root@192.168.0.202 "qm restart 101"

# Stop VM
ssh root@192.168.0.202 "qm stop 101"

# Check status
ssh root@192.168.0.202 "qm status 101"
```

## To Do
- [ ] Verify SSH access configuration
- [ ] Document installed software stack
- [ ] Add specific use-case documentation
- [ ] Configure backup if needed
