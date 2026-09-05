# jeffrey-dev — Development VM

**Last verified:** 2026-09-05 at the Proxmox configuration level. Seykhl VM
101 is stopped; no live guest address or software stack was verified. Sefer
VM 101 is a different guest, LiteLLM. Historical IP `.132` and software notes
below are not proof of current reachability.

## Overview
`jeffrey-dev` (VMID 101) is a development VM on Proxmox host `seykhl`. It is a general-purpose development environment.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 101 |
| **Name** | jeffrey-dev |
| **OS** | Not reverified while stopped; old records disagree (Debian 13 vs Ubuntu 26.04) |
| **CPU** | host |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 20GB (local-lvm, scsi0) |
| **Network** | vmbr0 (DHCP), virtio |
| **MAC** | BC:24:11:CD:26:F7 |
| **LAN IP** | 192.168.0.132 |
| **Hostname** | jeffrey-dev |
| **Status** | Stopped (verified 2026-09-05) |

## Access

### SSH
The VM is configured with cloud-init but may not have the same SSH key as other VMs. Access via:

```bash
# Via Proxmox console
ssh root@192.168.20.202 "qm console 101"

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
ssh root@192.168.20.202 "qm console 101"

# Restart VM
ssh root@192.168.20.202 "qm restart 101"

# Stop VM
ssh root@192.168.20.202 "qm stop 101"

# Check status
ssh root@192.168.20.202 "qm status 101"
```

## To Do
- [ ] Verify SSH access configuration
- [ ] Document installed software stack
- [ ] Add specific use-case documentation
- [ ] Configure backup if needed
