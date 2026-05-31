# SSH Enable HowTo — Mount VM Disk Offline

## Problem
You create a VM from a Debian/Ubuntu cloud image on Proxmox. Cloud-init creates the user but locks SSH to **public-key-only authentication**. You don't have console access, and `ssh-copy-id` fails because password auth is disabled.

## Solution
Stop the VM, mount its disk directly from the Proxmox host, and write your SSH public key into the user's `authorized_keys` file. This bypasses all authentication hurdles.

## Prerequisites
- Proxmox host access (root)
- The VM is stopped (or you can stop it)
- You know the user's UID (cloud-init users are typically UID 1000)

## Steps

### 1. Stop the VM
```bash
qm stop <vmid>
```

### 2. Find the VM disk
```bash
ls /dev/pve/vm-<vmid>-disk-0
# e.g., /dev/pve/vm-103-disk-0
```

### 3. Mount the root partition
Cloud images use GPT with boot partitions. The root partition starts at offset **134217728 bytes** (256 sectors × 512 bytes).

```bash
# Create a loop device starting at the root partition offset
losetup -f --show --offset=134217728 /dev/pve/vm-<vmid>-disk-0
# Output: /dev/loop0

# Mount it
mount /dev/loop0 /mnt/vm103
```

### 4. Inject your SSH key
```bash
# Create .ssh directory
mkdir -p /mnt/vm103/home/<username>/.ssh
chmod 700 /mnt/vm103/home/<username>/.ssh

# Write your public key
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... your@email.com" \
  > /mnt/vm103/home/<username>/.ssh/authorized_keys
chmod 600 /mnt/vm103/home/<username>/.ssh/authorized_keys

# Fix ownership (UID 1000 for the first cloud-init user)
chown -R 1000:1000 /mnt/vm103/home/<username>/.ssh
```

### 5. Clean up and restart
```bash
umount /mnt/vm103
losetup -d /dev/loop0
qm start <vmid>
```

### 6. SSH in
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null <username>@<vm-ip>
```

## Why This Works
- Cloud-init images always enable `sshd` and always allow key authentication
- Writing `authorized_keys` directly is the **fastest, most reliable** way to get in
- No need to fight with `PasswordAuthentication`, cloud-init password quirks, or corrupted config files
- Works even if the VM has never been logged into

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| **Wrong offset** | If `mount` fails, inspect partitions with `fdisk -l /dev/pve/vm-NNN-disk-0` and calculate the correct offset |
| **Wrong UID** | Check `grep <username> /mnt/vm103/etc/passwd` to get the correct UID for `chown` |
| **Corrupted sshd_config** | Don't try to edit `sshd_config` on a running VM's mounted disk — it can get corrupted. Just inject the key and fix SSH config later from inside |
| **Permission denied (key)** | Ensure `authorized_keys` is mode `600` and `.ssh` is mode `700` |

## Alternative: Fix Password Auth
If you really need password auth (not recommended for automation):

```bash
# While disk is mounted, fix the password hash
chroot /mnt/vm103 /bin/bash -c "echo '<username>:<password>' | chpasswd"
```

This is less reliable because cloud-init may overwrite it on next boot.

## Full Example (homestar-runner, VMID 103)

```bash
ssh root@seykhl

qm stop 103

losetup -f --show --offset=134217728 /dev/pve/vm-103-disk-0
mount /dev/loop0 /mnt/vm103

mkdir -p /mnt/vm103/home/stephen/.ssh
chmod 700 /mnt/vm103/home/stephen/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBoBSMwr4DtS0F8gzJPJCm0CMZIhvpsyamSfyHAX/A+S stephen.barr@devfactory.com" \
  > /mnt/vm103/home/stephen/.ssh/authorized_keys
chmod 600 /mnt/vm103/home/stephen/.ssh/authorized_keys
chown -R 1000:1000 /mnt/vm103/home/stephen/.ssh

umount /mnt/vm103
losetup -d /dev/loop0
qm start 103

# From your laptop
ssh stephen@192.168.0.154
```

## Resources
- Proxmox Cloud-Init Docs: https://pve.proxmox.com/wiki/Cloud-Init_Support
- Proxmox Disk Management: https://pve.proxmox.com/wiki/Storage
- SSH Authorized Keys: https://en.wikipedia.org/wiki/Authorized_keys
