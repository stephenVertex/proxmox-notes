# test-full-201 — Test/Experimental VM

## Overview
`test-full-201` (VMID 203) is a test VM on Proxmox host `seykhl`. It is currently stopped and used for experimental purposes.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 203 |
| **Name** | test-full-201 |
| **OS** | Linux (L26) |
| **CPU** | x86-64-v2-AES |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 33GB (local-lvm, scsi0) |
| **Network** | vmbr0 (DHCP), virtio, firewall enabled |
| **MAC** | BC:24:11:67:9C:B6 |
| **LAN IP** | N/A (currently stopped) |
| **Status** | Stopped |
| **Template** | No |
| **Cloud-Init** | Enabled (user: opensymphony) |

## Access

### Proxmox Console
```bash
ssh root@192.168.0.202 "qm console 203"
```

### SSH (when running)
```bash
ssh opensymphony@<ip-address>
```

**Note:** This VM uses the `opensymphony` user, not `stephen`. SSH keys are configured via cloud-init.

## Network Details
- **LAN IP:** Assigned via DHCP when running
- **MAC:** BC:24:11:67:9C:B6
- **Bridge:** vmbr0
- **Firewall:** Enabled
- **DNS:** Will be added to `/etc/hosts` when active

## Purpose
- Test environment for experimental configurations
- Used for testing new software stacks before deploying to production VMs
- Can be used as a sandbox for risky operations

## Notes
- Currently stopped to save resources
- Has firewall enabled on network interface
- Created with cloud-init for automated setup
- Not a template (can be converted to template if needed)

## Maintenance
```bash
# Start VM
ssh root@192.168.0.202 "qm start 203"

# Stop VM
ssh root@192.168.0.202 "qm stop 203"

# Check status
ssh root@192.168.0.202 "qm status 203"

# Get IP when running
ssh root@192.168.0.202 "ip neigh | grep bc:24:11:67:9c:b6"

# Convert to template (if needed)
ssh root@192.168.0.202 "qm template 203"
```

## To Do
- [ ] Document what experiments are being tested
- [ ] Convert to template if it's a base image
- [ ] Add to monitoring if needed for production use
- [ ] Document SSH key configuration
