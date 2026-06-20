# Proxmox TODO

## [ ] Backup / Disaster Recovery

**Goal:** If seykhl burned up, buy a replacement machine and fully restore the fleet.

### What needs backing up

- **VM disks** — all VMs (100–111) stored in the local-lvm thin pool across nvme0n1 + sda
- **Proxmox host config** — `/etc/pve/` (VM configs, network, storage definitions, cluster state)
- **VM-internal data that lives outside the thin pool:**
  - doltsvr (VM 100) — Dolt databases
  - yesod-postgres-server (VM 102) — PostgreSQL data
  - n8n-server (VM 107) — workflows + credentials
  - homestar-runner (VM 103), jeffrey-dev (VM 101) — anything stateful
- **seykhl host itself** — any config not in /etc/pve (cron, custom packages, etc.)

### Options to evaluate

- **Proxmox Backup Server (PBS)** — purpose-built, deduplicating, incremental VM backups; can run in a VM or on a second machine; backed up to NAS or S3-compatible storage
- **vzdump to remote** — Proxmox built-in tool; `vzdump` can snapshot and stream a VM backup to a remote SSH/NFS/CIFS target; simpler, no extra server needed
- **Proxmox built-in scheduled backups** — GUI-configurable, uses vzdump under the hood; can write to local dir, NFS, or PBS
- **Offsite storage target** — NAS on LAN (Synology/TrueNAS), S3 bucket, Backblaze B2, or rclone to any cloud
- **Bare-metal restore path** — document: "buy machine X, install Proxmox, restore from backup, fleet is up in N hours"

### Questions to answer before designing the solution

1. Where does the backup live? (same LAN NAS, offsite cloud, both?)
2. How much data? (thin pool is ~635 GB provisioned but actual used space is much less — run `lvs` to check)
3. RTO/RPO: how stale can a restore be? (daily? hourly?)
4. Do we want full VM snapshots or just the stateful data (postgres, dolt, n8n)?
5. Is a second Proxmox host (or a VPS running PBS) on the table?

### Immediate quick-win (no design needed)

- [ ] Run `vzdump` on the highest-value VMs (doltsvr, postgres, n8n) manually at least once to a local dir — proves the tooling works before building automation
