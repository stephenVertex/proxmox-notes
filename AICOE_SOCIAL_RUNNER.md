# aicoe-social-runner — Social-Media Engagement Monitor Runner

## Overview
`aicoe-social-runner` (VMID 105) is a Debian 13 VM on Proxmox host `seykhl`. It is a
dedicated, headless cron runner for the **engage-watch** agent
(`sjb-agentic-social-media-monitor`) — a scheduled AI agent that monitors
social-media engagement via `aysp` and reports findings to Synapse org-memory.

It runs the Synapse agent identity `agent.aicoe-social-monitor` under
`project.social-monitoring` / `team.ai-coe`.

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 105 |
| **Name** | aicoe-social-runner |
| **OS** | Debian 13 "Trixie" (cloud image) |
| **CPU** | host |
| **Cores** | 2 |
| **Memory** | 2GB (balloon 1GB) |
| **Disk** | 20GB (local-lvm, scsi0) |
| **Network** | vmbr0 (DHCP), virtio |
| **MAC** | BC:24:11:A4:CE:80 |
| **LAN IP** | 192.168.0.147 |

## Why so small
The runner stores no data. `aysp`'s analytics live in a remote Supabase DB and
the Synapse API is cloud-hosted, so the VM only shells out to two CLIs on a
4-hour cron. 2GB/2-core/20GB is ample.

## SSH Access
```bash
ssh stephen@192.168.0.147     # or: ssh stephen@aicoe-social-runner (after /etc/hosts)
```
Key-based (cloud-init injected the ed25519 key); passwordless sudo.

## Build Log (2026-06-04)
Created via cloud-init (not the offline-disk-mount method — this image takes
`sshkeys`/`ciuser` directly):
```bash
ssh root@seykhl
qm create 105 --name aicoe-social-runner --memory 2048 --balloon 1024 \
  --cores 2 --cpu host --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-single --ostype l26 --agent enabled=1
qm importdisk 105 /var/lib/vz/template/iso/debian-13-generic-amd64.qcow2 local-lvm
qm set 105 --scsi0 local-lvm:vm-105-disk-0 --boot order=scsi0
qm set 105 --ide2 local-lvm:cloudinit --ipconfig0 ip=dhcp --ciuser stephen \
  --sshkeys /root/ci/social-runner.pub
qm resize 105 scsi0 20G
qm start 105
```

## Software Installed
| Tool | How | Notes |
|------|-----|-------|
| git, cron, nodejs, npm | `apt` | base |
| uv | astral install script | `~/.local/bin/uv`; manages Python |
| synapse-cli 0.3.5 | `npm i -g github:dp-pcs/synapse-cli` | `/usr/local/bin/synapse-cli` |
| aysp 0.1.9 | `uv tool install ~/dev/ayrshare-simple` | `~/.local/bin/aysp` |
| engage-watch | `git clone … && uv sync` | `~/dev/sjb-agentic-social-media-monitor` |

GitHub access: the VM's ed25519 key was added as an **account SSH key** on
`stephenVertex` (both source repos are private). Listed in
GitHub → Settings → SSH keys as "aicoe-social-runner (VM105)".

## Secrets (provisioned out-of-band, NOT in any repo)
| Secret | Location on VM | Source |
|--------|----------------|--------|
| aysp Supabase URL + service-role key, Ayrshare API key | `~/.config/ayrshare/config.json` (0600) | scp'd from Mac |
| aysp profile keys | `~/.config/ayrshare/profiles.json` (0600) | scp'd from Mac |
| Synapse bearer token | `~/.config/synapse/aicoe-social-monitor.token` (0600) | from Mac Keychain |

Synapse token resolution on Linux (no Keychain) uses a **resolver executable**:
`~/.config/synapse/resolvers/aicoe-social-monitor` (0700) that `cat`s the token
file. synapse-cli tries resolvers before Keychain/env, so this just works.

## Cron
```
0 */4 * * * /home/stephen/dev/sjb-agentic-social-media-monitor/scripts/cron-run.sh
```
The wrapper derives its repo dir from its own path (portable Mac/Linux), pins
PATH, runs `smm-monitor run --profile AIFS`, and appends to
`~/.local/share/smm-monitor/cron.log`. Synapse reporting is ON by default
(`SMM_SYNAPSE=0` to disable). Local run history: `~/.local/share/smm-monitor/runs.jsonl`.

## Verification
```bash
ssh stephen@192.168.0.147
cd ~/dev/sjb-agentic-social-media-monitor
synapse-cli doctor        # binding -> token (via resolver) -> ping -> brief.fetch
uv run smm-monitor doctor # aysp ok, synapse ok, result: ready
```
Both pass green as of 2026-06-04.

## Updating the agent
```bash
ssh stephen@192.168.0.147
cd ~/dev/sjb-agentic-social-media-monitor && git pull && uv sync
# aysp updates:
cd ~/dev/ayrshare-simple && git pull && uv tool install --reinstall .
```

## Resources
- Proxmox host: `seykhl` (192.168.0.202)
- engage-watch repo: https://github.com/stephenVertex/sjb-agentic-social-media-monitor (private)
- aysp repo: https://github.com/stephenVertex/ayrshare-simple (private)
- Synapse: https://cnu.synapse-os.ai (project.social-monitoring / team.ai-coe)

## Notes
- No `qemu-guest-agent` (not in default Debian 13 repos); IP found via MAC on host ARP.
- Per-post `aysp analytics` calls are slow over the VM→Supabase link (each spawns
  a fresh Python process). A full run takes a few minutes; fine for a 4h cron.
  Future optimization: a batch analytics read in aysp would cut this dramatically.
