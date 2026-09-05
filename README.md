# Proxmox Infrastructure Overview

**Last verified:** 2026-09-05 against the live hosts and guests.

`sefer` and `seykhl` are both active, separate Proxmox hosts. Sefer hosts the
production services and most execution infrastructure; Seykhl hosts nine g2
gate VMs and retains stopped legacy guests. The complete current inventory is
in [INVENTORY.md](INVENTORY.md), with network details in [NETWORK.md](NETWORK.md).
The editable [network diagram](yesod-network.drawio) includes the current
physical layout on the **Copy of 1 - Current cabling** tab; the other tabs
retain earlier layouts and proposals.

## Hosts and networks

| Setting | Sefer | Seykhl |
|---|---|---|
| VLAN 20 address | `192.168.20.10/24`, `vmbr1` | `192.168.20.202/24`, `vmbr0` |
| Additional connection | Direct 10 GbE: `192.168.0.100/24`, `vmbr0` | None observed |
| Default gateway | `192.168.0.1` on direct 10 GbE side | `192.168.20.1` |
| Proxmox | VE 9.2.2, kernel `7.0.2-6-pve` | VE 9.1.1, kernel `6.17.2-1-pve` |
| CPU | 2 × Xeon Gold 6152; 44 cores / 88 threads | Xeon W-2123; 4 cores / 8 threads |
| Installed RAM | 251 GiB | 78 GiB |
| VMs | 47 configured, 31 running | 21 configured, 9 running |
| LXC | 21 configured, 19 running | 1 stopped template |

Sefer is the Dell PowerEdge R740xd. Both hosts participate in `192.168.20.0/24`,
while Sefer retains its separate direct 10 GbE connection. Most Sefer guests
remain on `192.168.0.0/24`; PostgreSQL, Dertog, Dolt primary and the g2 test
databases use its VLAN bridge. Seykhl's guests use VLAN 20.

```bash
ssh -o BatchMode=yes root@192.168.20.10
ssh -o BatchMode=yes root@192.168.20.202
```

## Production and supporting services

These are all on Sefer. Addresses are observed guest IPv4 addresses; database
listener restrictions are documented per service.

| VM | Service | Guest IPv4 | Documentation |
|---:|---|---|---|
| 100 | Isolated Dolt static seed, SQL disabled | `192.168.0.160` | [Dolt standby](DOLT_STANDBY.md) |
| 101 | LiteLLM gateway, broker and dashboards | `192.168.0.157` | [LiteLLM](LITELLM_GATEWAY.md) |
| 102 | Production PostgreSQL | `192.168.20.155` | [PostgreSQL](YESOD_POSTGRES_SERVER.md) |
| 103 | Five GitHub Actions runner services | `192.168.0.154` | [GitHub runners](SEYKHL_ACTIONS_RUNNER.md) |
| 104 | Dertog dashboards and Yesod API | `192.168.20.138` | [Dertog](DERTOG.md) |
| 105 | Social monitor cron runner | `192.168.0.147` | [Social runner](AICOE_SOCIAL_RUNNER.md) |
| 107 | n8n | `192.168.0.145` | [n8n](N8N_SERVER.md) |
| 111 | Supabase APIs, runtime, realtime and storage | `192.168.0.137` | [sb-edge](SB_EDGE.md) |
| 113 | DocuSeal | `192.168.0.139` | [DocuSeal](DOCUSEAL.md) |
| 114 | draw.io | `192.168.0.149` | [draw.io](DRAWIO.md) |
| 116 | RSSHub; Miniflux currently stopped | `192.168.0.169` | [Bukher](BUKHER.md) |
| 117 | SigNoz | `192.168.0.163` | [Observability](OBS_VULTR.md) |
| 118 | Neo4j | `192.168.0.167` | [Neo4j](NEO4J.md) |
| 119 | GitLab EE | `192.168.0.170` | [GitLab](GITLAB.md) |
| 120 | GitLab Docker group runner | `192.168.0.171` | [GitLab Runner](GITLAB.md#gitlab-runner) |
| 121 | Semantic graph controller / pipeline PostgreSQL | `192.168.0.172` | [Semantic graph](YESOD_SEMANTIC_GRAPH.md) |
| 124 | Production Dolt primary | `192.168.20.150` | [Dolt primary](DOLT_SERVER.md) |

[YESOD-RUNNER.md](YESOD-RUNNER.md) covers runner-3 (110), Ibur (130), Golem
(131), Lamedvov (150), Tzadik (151), dispatch/refinery (152), the g1/g2 gate
fleet and their PostgreSQL test containers. [INVENTORY.md](INVENTORY.md) also
lists every stopped VM and template. Jeffrey-dev remains stopped on Seykhl;
DynamoDB CT 115 and the old OpenSymphony/test VMs are absent.

## Storage

| Host/storage | Backing | Observed allocation | Use |
|---|---|---|---|
| Sefer `rpool` | Mirror: 2 × 240 GB Intel SATA SSD | 127 GiB of 220 GiB | Host and `local`; raw VM disks 102, 104, 124 |
| Sefer `vmdata` | Mirror: 2 × 1 TB Samsung 970 EVO Plus NVMe | 339 GiB of 928 GiB | Remaining VM disks |
| Sefer `scratch` | Single 1 TB Seagate IronWolf SSD | 6.42 GiB of 928 GiB | Disposable PostgreSQL containers; no redundancy |
| Sefer `nas-backups` | NAS directory `/mnt/proxmox-backups` | ~15.1 TiB used of 31.4 TiB | Backup archives |
| Seykhl `local-lvm` | LVM thin pool | ~67.7% used of 634 GiB | g2 gates and retained legacy disks |

All three Sefer ZFS pools report `ONLINE` with no known data errors. Sefer's
direct 10 GbE connection provides the NAS path. The production disks are no
longer all on `vmdata`; free space is a snapshot, not reserved capacity.

## Backups and observed issues

The configured Sefer jobs still cover only the original 12 guests:

| Job | Schedule (Pacific) | VMs | Configured retention |
|---|---|---|---|
| `sefer-light-services` | Daily 03:30 | 100,103,105,107,113,114,116,117,118,119,120 | 7 daily / 4 weekly / 3 monthly |
| `yesod-semantic-graph` | Daily 04:30 | 121 | 7 daily / 4 weekly / 3 monthly |

Both September 5 jobs reported **job errors during pruning**: archive transfer
completed, but deleting older NAS archives returned `Operation not supported`.
Configured retention must not be described as successfully enforced. See
[BACKUPS.md](BACKUPS.md) for the evidence and coverage gaps.

The GitLab-native backup completed successfully at 01:31 Pacific, and the
semantic graph logical PostgreSQL dump completed at 04:15. Those successful
application backups are separate from the Proxmox job results.

Seykhl still has backup cron entries for old VM IDs and old Dolt/PostgreSQL
addresses. The migrated production VMs, LiteLLM and expanded runner fleet are
absent from Sefer's scheduled VM backup lists.

Additional observations:

- PostgreSQL was being repaired during this audit. Its stale-address startup
  failure was corrected in the live drop-in; final listener evidence is in
  [YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md).
- Miniflux is stopped after failing to bind its Tailscale address at startup.
- Ibur and the main dispatch/refinery services recovered during the database
  repairs. Other inactive or failed components are recorded per service;
  VM uptime alone does not establish application health.
- Nine running Sefer VMs have no responding QEMU guest agent. Stopped legacy
  copies retain conflicting IPs or autostart flags; see [inventory cautions](INVENTORY.md#configuration-cautions).

## Documentation scope

Current service pages and the live inventory supersede old build logs. Dated
provisioning records and long-term plans retain historical commands under
explicit notices; they do not authorize starting old copies. External DNS,
billing, router reservations and application data correctness were not
re-audited as part of the host/service inventory. Installed version observations
are in [VERSION_UPGRADES.md](VERSION_UPGRADES.md).
