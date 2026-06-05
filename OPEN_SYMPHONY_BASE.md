# opensymphony-base — Test/Experimental Base VM

## Overview
`opensymphony-base` (VMID 205) is a test/template VM on Proxmox host `seykhl`. It is currently stopped and may be used as a base image for other VMs.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 205 |
| **Name** | opensymphony-base |
| **OS** | Linux (L26) |
| **CPU** | x86-64-v2-AES |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 33GB (local-lvm, base-205-disk-0) |
| **Network** | vmbr0 (DHCP), virtio, firewall enabled |
| **MAC** | BC:24:11:4A:19:61 |
| **LAN IP** | N/A (currently stopped) |
| **Status** | Stopped |
| **Template** | Yes (marked as template) |
| **Cloud-Init** | Enabled (user: opensymphony) |

## Access

### Proxmox Console
```bash
ssh root@192.168.0.202 "qm console 205"
```

### SSH (when running)
```bash
ssh opensymphony@<ip-address>
```

**Note:** This VM uses the `opensymphony` user, not `stephen`. SSH keys are configured via cloud-init.

## Network Details
- **LAN IP:** Assigned via DHCP when running
- **MAC:** BC:24:11:4A:19:61
- **Bridge:** vmbr0
- **Firewall:** Enabled
- **DNS:** Will be added to `/etc/hosts` when active

## Purpose
- Base template for creating new VMs
- Can be cloned to quickly provision new instances
- May be used for testing opensymphony-related configurations

## Notes
- Currently stopped to save resources
- Marked as a template in Proxmox
- Has firewall enabled on network interface
- Created with cloud-init for automated setup
- Uses a base disk image (base-205-disk-0) rather than a regular VM disk

## Maintenance
```bash
# Start VM (if you need to modify the template)
ssh root@192.168.0.202 "qm start 205"

# Stop VM
ssh root@192.168.0.202 "qm stop 205"

# Check status
ssh root@192.168.0.202 "qm status 205"

# Clone template to new VM
ssh root@192.168.0.202 "qm clone 205 <new-vmid> --name <new-name>"

# Get IP when running
ssh root@192.168.0.202 "ip neigh | grep bc:24:11:4a:19:61"
```

## To Do
- [ ] Document what the base image contains
- [ ] Verify template functionality (clone test)
- [ ] Add to monitoring if needed for production use
- [ ] Document SSH key configuration for opensymphony user
- [ ] Consider converting to a proper Proxmox template if not already
