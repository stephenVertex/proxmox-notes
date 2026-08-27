# Proxmox Infrastructure Overview

**Last verified:** 2026-08-27

## Current Proxmox host: `sefer`

`sefer` is the active single-node Proxmox host. It replaced the former
`seykhl` node; documents describing `seykhl` are historical unless explicitly
updated below.

| Setting | Value |
|---|---|
| Hostname / LAN IP | `sefer` / `192.168.0.100` |
| Hardware | Dell PowerEdge R740xd |
| Proxmox | VE 9.2.2 on Debian 13 (Trixie), kernel `7.0.2-6-pve` |
| CPU | 2 × Intel Xeon Gold 6152: 44 physical cores / 88 threads |
| Memory | 251 GiB installed; ~218 GiB available at verification |
| Network | `vmbr0` on `192.168.0.0/24` |
| Cluster | Single node |

Access the web UI at `https://192.168.0.100:8006`, or use:

```bash
ssh root@sefer
qm list
pct list
```

## Virtual machines

All listed disks are on the `vmdata` ZFS pool. All eight running service VMs
are configured to start at boot and have the Proxmox guest agent enabled in
their VM configuration.

| VMID | Name | State | vCPU | RAM | Disk | LAN IP | Purpose |
|---:|---|---|---:|---:|---:|---|---|
| 103 | `seykhl-actions-runner` | running | 2 | 4 GiB | 30 GiB | 192.168.0.154 | Five self-hosted GitHub Actions runners |
| 105 | `aicoe-social-runner` | running | 2 | 2 GiB | 20 GiB | 192.168.0.147 | Social-engagement monitor cron runner |
| 107 | `n8n-server` | running | 2 | 4 GiB | 30 GiB | 192.168.0.145 | n8n automation |
| 113 | `docuseal` | running | 1 | 2 GiB | 20 GiB | 192.168.0.139 | DocuSeal signing service |
| 114 | `drawio` | running | 1 | 2 GiB | 20 GiB | 192.168.0.149 | draw.io diagram editor |
| 116 | `bukher` | running | 2 | 4 GiB | 30 GiB | 192.168.0.169 | RSSHub and Miniflux ingestion |
| 117 | `obs-vultr` | running | 8 | 16 GiB | 120 GiB | 192.168.0.163 | SigNoz observability stack |
| 118 | `neo4j` | running | 4 | 16 GiB | 100 GiB | 192.168.0.167 | Neo4j graph database |
| 201 | `yesod-runner-4-codex` | stopped | 16 | 48 GiB | 64 GiB | — | Codex runner image |
| 202 | `yesod-runner-5-claude` | stopped | 16 | 48 GiB | 64 GiB | — | Claude runner image |
| 203 | `yesod-runner-6-opencode-fw` | stopped | 16 | 48 GiB | 64 GiB | — | OpenCode firewall runner image |
| 9000 | `yesod-runner-template` | stopped | 8 | 24 GiB | 64 GiB | — | Yesod runner template |

There are no LXC containers on `sefer`.

## Storage and backups

| Storage | Type | Live state at verification | Use |
|---|---|---|---|
| `rpool` | ZFS mirror, 2 × 240 GB Intel SATA SSDs | 220 GB total; 2.65 GB allocated; healthy | Proxmox boot/system storage (`local`, `local-zfs`) |
| `vmdata` | ZFS mirror, 2 × 1 TB Samsung 970 EVO Plus NVMe SSDs | 928 GB total; 59.6 GB allocated; healthy | All VM disks |
| `nas-backups` | NAS directory storage | 31.4 TiB total; 14.5 TiB used; 16.9 TiB free | Proxmox backups |

One 1 TB Seagate IronWolf SATA SSD is visible to the host but is not a member
of either reported ZFS pool.

The enabled `sefer-light-services` job creates `zstd` snapshot backups to
`nas-backups` daily at 03:30 for VMs 103, 105, 107, 113, 114, 116, 117, and
118. Retention is 7 daily, 4 weekly, and 3 monthly backups. This protects the
VMs; stateful services should still have application-consistent recovery
procedures (especially SigNoz and Neo4j).

## Service documentation

| Service | Documentation |
|---|---|
| GitHub Actions runner (VM 103) | [SEYKHL_ACTIONS_RUNNER.md](SEYKHL_ACTIONS_RUNNER.md) |
| AICOE social runner (VM 105) | [AICOE_SOCIAL_RUNNER.md](AICOE_SOCIAL_RUNNER.md) |
| n8n (VM 107) | [N8N_SERVER.md](N8N_SERVER.md) |
| DocuSeal (VM 113) | [DOCUSEAL.md](DOCUSEAL.md) |
| draw.io (VM 114) | [DRAWIO.md](DRAWIO.md) |
| Bukher (VM 116) | [BUKHER.md](BUKHER.md) |
| SigNoz observability (VM 117) | [OBS_VULTR.md](OBS_VULTR.md) |
| Neo4j (VM 118) | [NEO4J.md](NEO4J.md) |

## Planned services

| Service | Documentation |
|---|---|
| GitLab on `makor.meshcrawler.com` | [GITLAB.md](GITLAB.md) — proposed; not yet provisioned |

## Operational notes

- `docuseal` and `bukher` did not respond to the QEMU guest-agent query during
  the 2026-08-27 inventory, despite `agent: enabled=1` in their VM
  configuration. Use SSH or the Proxmox console for those guests until the
  in-guest agent is repaired.
- The local `docuseal` and `obs-vultr` SSH aliases have stale host-key entries;
  verify each new fingerprint through the Proxmox console before replacing the
  local trusted key. `neo4j` currently has no local SSH alias.
- The current Dell-host deployment supersedes the planned migration in
  [DELL_POWEREDGE_NEW_PROXMOX.md](DELL_POWEREDGE_NEW_PROXMOX.md), which is kept
  as a historical procurement record.
