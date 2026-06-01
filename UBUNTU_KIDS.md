# Ubuntu Kids Setup Log

## Objective
Create an Ubuntu VM named `jeffrey-dev` on Proxmox server `seykhl` (192.168.0.202).
- No X (headless/server)
- Latest Ubuntu release

## Environment
- Proxmox: pve-manager/9.1.1
- Storage: `local` (dir), `local-lvm` (lvmthin)
- Network bridge: `vmbr0`
- Existing VM: 100 (dolt-server)

## Actions

### 1. Initial Survey
- SSH to root@seykhl works.
- Storage pools: local, local-lvm
- Network: vmbr0 bridge available
- Next VMID available: 101

### 2. Latest Ubuntu Release
- Checked https://cloud-images.ubuntu.com/
- Available releases include `noble` (24.04), `questing` (25.10), `resolute` (26.04)
- **Selected: Ubuntu 26.04 (Resolute Rat)** — the latest release.
- Cloud image URL: https://cloud-images.ubuntu.com/resolute/current/resolute-server-cloudimg-amd64.img

### 3. Download Cloud Image
- Downloaded `resolute-server-cloudimg-amd64.img` to `/var/lib/vz/template/iso/` on Proxmox.
- Size: ~857 MB (3.5 GB when uncompressed/imported).

### 4. Create VM
- VMID: 101
- Name: `jeffrey-dev`
- Memory: 4096 MB
- Cores: 2
- Network: `virtio` bridge on `vmbr0`

### 5. Import and Configure Disk
- Imported cloud image into `local-lvm` storage as `vm-101-disk-0`.
- Attached as `scsi0` with `virtio-scsi-pci` controller.
- Added cloud-init CDROM on `ide2`.
- Set boot order: `boot c`, `bootdisk scsi0`.
- Resized disk from 3.5 GB to **20 GB**.

### 6. Cloud-Init Configuration
- User: `jeffrey`
- SSH key: injected local `id_ed25519.pub` for passwordless SSH.
- Network: DHCP (default).

### 7. Serial Console (Headless)
- Added `serial0 socket` and `vga serial0` for console access via `qm terminal 101`.
- Enabled QEMU guest agent (`agent enabled=1`) for better integration.

### 8. Headless Verification
- No display manager running.
- No Xorg processes found.
- Ubuntu cloud server image is headless by default (no GUI installed).

### 9. Network Assignment
- MAC: `BC:24:11:CD:26:F7`
- IP: **192.168.0.147** (DHCP)
- Verified via `nmap -sn 192.168.0.0/24` on Proxmox host.

### 10. Verification
- SSH as `jeffrey@192.168.0.147` works passwordlessly.
- `hostname`: `jeffrey-dev`
- `lsb_release -d`: `Ubuntu 26.04 LTS`

### 11. User Setup
- Set password for `jeffrey`: `jeffrey14!`
- Added `jeffrey` to `sudo` group (`usermod -aG sudo jeffrey`).
- Root password is locked (`*` in `/etc/shadow`); root access only via `sudo`.

### 12. Node.js / npm Installation
- Installed Node.js **v24.15.0** via NodeSource repo (`setup_24.x`).
- npm version: **11.12.1**.

### 13. OpenCode Installation
- Installed via `curl -fsSL https://opencode.ai/install | bash`.
- Version: **1.15.4**
- Binary: `/home/jeffrey/.opencode/bin/opencode`
- PATH added to `~/.bashrc`.

### 14. OpenCode Troubleshooting
**Problem: OOM Killed / Illegal Instruction**
- Initially, opencode was killed by the OOM killer on 4 GB RAM.
- After bumping to 8 GB, it crashed with `Illegal instruction (core dumped)`.
- Root cause: **CPU type** — default Proxmox `kvm64` does not expose AVX/AVX2 to guests.
- Bun (the runtime opencode is built on) requires AVX/AVX2 CPU features.
- **Fix:** Changed VM CPU type from `kvm64` to **`host`** (`qm set 101 --cpu host`).
- CPU passthrough exposes AVX/AVX2/AVX-512 from the Intel Xeon W-2123.

**Tested with 4 GB RAM:**
- After the CPU fix, reduced VM memory back to **4 GB**.
- Opencode starts successfully and reports `1.15.4`.
- The earlier OOM was likely triggered by Bun's fallback path when AVX was missing.

### 15. Memory Allocation Note
- Proxmox host (`seykhl`) has **30 GB** total RAM.
- VM 100 (`dolt-server`): allocated **24 GB**.
- VM 101 (`jeffrey-dev`): allocated **4 GB**.
- Total allocated: **28 GB** (under host total, comfortable margin).
- Proxmox supports memory overcommitment via ballooning.

### 16. Shutdown
- Cleanly shut down VM 101 via `qm shutdown 101`.
- Status: **stopped**.

## Result
VM `jeffrey-dev` (101) is configured on `seykhl`.
- Ubuntu 26.04 LTS (Resolute Rat)
- Headless server
- **RAM:** 4 GB
- **CPU:** `host` (AVX/AVX2/AVX-512 passthrough)
- **Status:** Stopped (ready to start with `qm start 101`)
- Accessible via SSH when running: `ssh jeffrey@192.168.0.147`
- Password: `jeffrey14!` / SSH key passwordless
- `jeffrey` has `sudo` privileges
- Console accessible via: `qm terminal 101` from Proxmox
- Node.js v24.15.0, npm 11.12.1 installed
- OpenCode 1.15.4 installed at `~/.opencode/bin/opencode`

---

## yesod-postgres-server (VMID 102) — Debian 13 PostgreSQL Server

### Creation
- **Date:** 2026-05-18
- **Proxmox Host:** seykhl (192.168.0.202)
- **OS:** Debian 13 "Trixie" (latest stable)
- **Cloud Image:** `debian-13-generic-amd64.qcow2`
- **VM Specs:** 6GB RAM, 2 cores, CPU `host`, 30GB disk, virtio NIC
- **MAC:** BC:24:11:00:88:F5
- **LAN IP:** 192.168.0.155 (DHCP)
- **Tailscale IP:** 100.115.10.68
- **Hostname:** yesod-postgres-server

### User
- **Username:** stephen
- **Password:** lj*123NM
- **SSH:** Passwordless key-based auth configured by user
- **Sudo:** yes

### PostgreSQL
- **Version:** PostgreSQL 17.10 (latest stable from Debian 13 repos)
- **Service:** `postgresql` (enabled and running)
- **Superuser:** `postgres`
- **App User:** `stephen` (with CREATEDB privilege)
- **App Database:** `stephen` (owned by stephen)
- **Socket:** `/var/run/postgresql` port 5432
- **TCP Listener:** `100.115.10.68:5432` (Tailscale interface)
- **Connect (local):** `psql -U stephen -d stephen` (via unix socket)
- **Connect (Tailscale):** `psql -U stephen -d stephen -h yesod-postgres-server`

### Tailscale
- **Status:** Joined to tailnet
- **Tailscale IP:** 100.115.10.68
- **Tailscale Name:** yesod-postgres-server
- **Access:** SSH and PostgreSQL reachable via Tailscale from any authenticated device

---

## dolt-server (VMID 100) — Ubuntu Dolt Server

### Backup Configuration
See [DOLT_SERVER.md](DOLT_SERVER.md) for full backup documentation.

- **In-VM backups**: Hourly dolt dumps to `/var/backups/dolt/`
- **NAS mirror**: Hourly rsync to Synology NAS
- **VM snapshots**: Weekly vzdump to NAS
- **WORM protection**: Enabled on NAS share

---

## dertog (VMID 104) — Debian 13 Dashboard Server

### Creation
- **Date:** 2026-05-18
- **Proxmox Host:** seykhl (192.168.0.202)
- **OS:** Debian 13 "Trixie" (latest stable)
- **Cloud Image:** `debian-13-generic-amd64.qcow2`
- **VM Specs:** 6GB RAM (ballooning, 2GB min), 2 cores, CPU `host`, 30GB disk, virtio NIC
- **MAC:** BC:24:11:90:A9:CC
- **IP:** 192.168.0.138 (DHCP)
- **Hostname:** dertog

### User
- **Username:** stephen
- **SSH:** Passwordless key-based auth via offline disk mount
- **Sudo:** Passwordless (configured via `/etc/sudoers.d/stephen`)

### Purpose
- Host dashboards at various ports
- Receive distilled data uploads from workstation
- Central visualization hub

### Notes
- Stock Debian 13 — dashboards to be added as needed
- Memory ballooning enabled for efficiency
- SSH host keys regenerated offline (first-boot race condition fix)
