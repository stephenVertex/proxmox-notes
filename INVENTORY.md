# Live Proxmox inventory

**Verified:** 2026-09-05, read-only from both hosts and running guests.

This is a point-in-time inventory, not a promise of application health. VMIDs
are local to each standalone Proxmox host: always specify the host with the ID.
Addresses below are observed guest addresses, not just cloud-init settings.
Stopped guests have no verified live address. See [NETWORK.md](NETWORK.md) for
the VLAN and Sefer's separate direct 10 GbE connection.

## Sources and scope

The inventory uses `pvesh get /nodes/<host>/qemu` and `/lxc`, each guest's
configuration, `qm guest cmd <id> network-get-interfaces`, `pct exec <id> --
ip -4 a`, and authenticated guest SSH where the QEMU agent is unavailable.
All running guests were inspected through SSH, guest execution, or container
execution. Service documents distinguish health responses from process status.
Stopped VMs/templates were not booted; their software versions and old IPs
were not revalidated. No infrastructure changes or test jobs were made.

RAM and disks are configured capacity; thin disks do not occupy all that space.
Autostart `no` includes omitted `onboot` (the default is disabled).

## sefer: virtual machines

47 configured; 31 running.

| ID | Name | State | vCPU | RAM GiB | Disk/storage | Bridge | Observed IPv4 | Autostart |
|---:|---|---|---:|---:|---|---|---|---|
| 100 | `doltsvr-sefer` | running | 4 | 24 | vmdata: 100G | vmbr0 | 192.168.0.160 | yes |
| 101 | `litellm-gateway` | running | 2 | 4 | vmdata: 64G | vmbr0 | 192.168.0.157 | yes |
| 102 | `yesod-postgres-server` | running | 2 | 6 | local: 120G | vmbr1 | 192.168.20.155 | yes |
| 103 | `seykhl-actions-runner` | running | 2 | 4 | vmdata: 30G | vmbr0 | 192.168.0.154 | yes |
| 104 | `dertog` | running | 2 | 6 | local: 30G | vmbr1 | 192.168.20.138 | yes |
| 105 | `aicoe-social-runner` | running | 2 | 2 | vmdata: 20G | vmbr0 | 192.168.0.147 | yes |
| 107 | `n8n-server` | running | 2 | 4 | vmdata: 30G | vmbr0 | 192.168.0.145 | yes |
| 110 | `yesod-runner-3` | running | 44 | 64 | vmdata: 160G | vmbr0 | 192.168.0.136 | no |
| 111 | `sb-edge` | running | 2 | 4 | vmdata: 20G | vmbr0 | 192.168.0.137 | no |
| 113 | `docuseal` | running | 1 | 2 | vmdata: 20G | vmbr0 | 192.168.0.139 | yes |
| 114 | `drawio` | running | 1 | 2 | vmdata: 20G | vmbr0 | 192.168.0.149 | yes |
| 116 | `bukher` | running | 2 | 4 | vmdata: 30G | vmbr0 | 192.168.0.169 | yes |
| 117 | `obs-vultr` | running | 8 | 16 | vmdata: 120G | vmbr0 | 192.168.0.163 | yes |
| 118 | `neo4j` | running | 4 | 16 | vmdata: 100G | vmbr0 | 192.168.0.167 | yes |
| 119 | `makor` | running | 8 | 24 | vmdata: 80G + vmdata: 300G | vmbr0 | 192.168.0.170 | yes |
| 120 | `makor-runner-docker-1` | running | 6 | 16 | vmdata: 120G | vmbr0 | 192.168.0.171 | yes |
| 121 | `yesod-semantic-graph` | running | 4 | 8 | vmdata: 64G | vmbr0 | 192.168.0.172 | yes |
| 122 | `doltsvr-rehearsal-20260824` | stopped | 4 | 24 | vmdata: 64G | none | — | no |
| 123 | `doltsvr-fresh-seed-20260827` | stopped | 4 | 24 | vmdata: 64G | none | — | no |
| 124 | `doltsvr` | running | 4 | 24 | local: 64G | vmbr1 | 192.168.20.150 | yes |
| 130 | `yesod-runner-g2-ibur` | running | 4 | 16 | vmdata: 160G | vmbr0 | 192.168.0.173 | no |
| 131 | `yesod-gate-g1-golem` | running | 36 | 48 | vmdata: 160G | vmbr0 | 192.168.0.185 | no |
| 150 | `yesod-runner-g1-lamedvov` | running | 4 | 16 | vmdata: 160G | vmbr0 | 192.168.0.189 | no |
| 151 | `yesod-runner-g1-tzadik` | running | 4 | 16 | vmdata: 160G | vmbr0 | 192.168.0.180 | no |
| 152 | `yesod-runner-g1-dispatch` | running | 4 | 8 | vmdata: 160G | vmbr0 | 192.168.0.192 | no |
| 201 | `yesod-runner-4-codex` | stopped | 16 | 48 | vmdata: 64G | vmbr0 | — | no |
| 202 | `yesod-runner-5-claude` | stopped | 16 | 48 | vmdata: 64G | vmbr0 | — | no |
| 203 | `yesod-runner-6-opencode-fw` | stopped | 16 | 48 | vmdata: 64G | vmbr0 | — | no |
| 211 | `yesod-gate-1` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 212 | `yesod-gate-2` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 213 | `yesod-gate-3` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 214 | `yesod-gate-4` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 215 | `yesod-gate-5` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 216 | `yesod-gate-6` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 217 | `yesod-gate-7` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 218 | `yesod-gate-8` | stopped | 8 | 16 | vmdata: 64G | vmbr0 | — | no |
| 231 | `yesod-gate-g1-samael` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.178 | no |
| 232 | `yesod-gate-g1-dybbuk` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.176 | no |
| 233 | `yesod-gate-g1-ashmedai` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.181 | no |
| 234 | `yesod-gate-g1-lilith` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.196 | no |
| 235 | `yesod-gate-g1-azazel` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.175 | no |
| 236 | `yesod-gate-g1-estrie` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.194 | no |
| 237 | `yesod-gate-g1-broxa` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.188 | no |
| 238 | `yesod-gate-g1-mazik` | running | 8 | 8 | vmdata: 64G | vmbr0 | 192.168.0.179 | no |
| 9000 | `yesod-runner-template` | template | 8 | 24 | vmdata: 64G | vmbr0 | — | no |
| 9100 | `yesod-node-template` | template | 8 | 8 | vmdata: 64G | vmbr0 | — | no |
| 9101 | `yesod-gate-g1-unborn` | template | 8 | 8 | vmdata: 64G | vmbr0 | — | no |

## sefer: containers

21 configured; 19 running.

| ID | Name | State | vCPU | RAM GiB | Disk/storage | Bridge | Observed IPv4 | Autostart |
|---:|---|---|---:|---:|---|---|---|---|
| 141 | `hosted-experiment-pg16` | running | 2 | 2 | scratch: 16G | vmbr0 | 192.168.0.191 | no |
| 220 | `test-db-g1-golem` | running | 8 | 8 | scratch: 16G | vmbr0 | 192.168.0.184 | no |
| 241 | `test-db-g1-samael` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.190 | no |
| 242 | `test-db-g1-dybbuk` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.195 | no |
| 243 | `test-db-g1-ashmedai` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.197 | no |
| 244 | `test-db-g1-lilith` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.183 | no |
| 245 | `test-db-g1-azazel` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.187 | no |
| 246 | `test-db-g1-estrie` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.121 | no |
| 247 | `test-db-g1-broxa` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.124 | no |
| 248 | `test-db-g1-mazik` | running | 4 | 4 | scratch: 16G | vmbr0 | 192.168.0.127 | no |
| 251 | `test-db-g2-samael` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.147 | no |
| 252 | `test-db-g2-dybbuk` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.149 | no |
| 253 | `test-db-g2-ashmedai` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.151 | no |
| 254 | `test-db-g2-lilith` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.153 | no |
| 255 | `test-db-g2-azazel` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.109 | no |
| 256 | `test-db-g2-estrie` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.157 | no |
| 257 | `test-db-g2-broxa` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.159 | no |
| 258 | `test-db-g2-mazik` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.161 | no |
| 259 | `test-db-g2-golem` | running | 4 | 4 | scratch: 16G | vmbr1 | 192.168.20.106 | no |
| 9010 | `pg16-test-template` | template | 2 | 2 | scratch: 16G | vmbr0 | — | no |
| 9011 | `test-db-g1-unborn` | template | 4 | 4 | scratch: 16G | vmbr0 | — | no |

## seykhl: virtual machines

21 configured; 9 running.

| ID | Name | State | vCPU | RAM GiB | Disk/storage | Bridge | Observed IPv4 | Autostart |
|---:|---|---|---:|---:|---|---|---|---|
| 100 | `doltsvr` | stopped | 4 | 24 | local-lvm: 64G | vmbr0 | — | yes |
| 101 | `jeffrey-dev` | stopped | 2 | 4 | local-lvm: 20G | vmbr0 | — | no |
| 102 | `yesod-postgres-server` | stopped | 2 | 6 | local-lvm: 120G | vmbr0 | — | yes |
| 104 | `dertog` | stopped | 2 | 6 | local-lvm: 30G | vmbr0 | — | yes |
| 106 | `yesod-runner-1` | stopped | 4 | 16 | local-lvm: 40G | vmbr0 | — | yes |
| 108 | `yesod-runner-2` | stopped | 4 | 16 | local-lvm: 56G | vmbr0 | — | yes |
| 109 | `yesod-runner-base` | template | 4 | 8 | local-lvm: 20G | vmbr0 | — | no |
| 110 | `yesod-runner-3` | stopped | 4 | 16 | local-lvm: 60G | vmbr0 | — | no |
| 111 | `do-not-start` | stopped | 2 | 4 | local-lvm: 20G | vmbr0 | — | no |
| 112 | `yesod-dispatch` | stopped | 2 | 8 | local-lvm: 64G | vmbr0 | — | yes |
| 113 | `litellm-broker-staging` | stopped | 4 | 8 | local-lvm: 40G | vmbr0 | — | no |
| 231 | `yesod-gate-g2-samael` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.163 | no |
| 232 | `yesod-gate-g2-dybbuk` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.164 | no |
| 233 | `yesod-gate-g2-ashmedai` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.100 | no |
| 234 | `yesod-gate-g2-lilith` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.101 | no |
| 235 | `yesod-gate-g2-azazel` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.102 | no |
| 236 | `yesod-gate-g2-estrie` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.103 | no |
| 237 | `yesod-gate-g2-broxa` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.104 | no |
| 238 | `yesod-gate-g2-mazik` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.105 | no |
| 239 | `yesod-gate-g2-golem` | running | 4 | 7 | local-lvm: 64G | vmbr0 | 192.168.20.107 | no |
| 9101 | `yesod-gate-g1-unborn` | template | 8 | 8 | local-lvm: 64G | vmbr0 | — | no |

## seykhl: containers

1 configured; 0 running.

| ID | Name | State | vCPU | RAM GiB | Disk/storage | Bridge | Observed IPv4 | Autostart |
|---:|---|---|---:|---:|---|---|---|---|
| 9011 | `test-db-g1-unborn` | template | 4 | 4 | local-lvm: 16G | vmbr0 | — | no |

## Configuration cautions

- Sefer VM 131 reports live `192.168.0.185`, while its cloud-init configuration
  still says `192.168.0.174`. Use the observed address; reconcile provisioning
  before rebuilding it.
- Stopped Sefer VMs 201–203 retain `.171`, `.172`, `.173` in cloud-init, which
  overlap the active GitLab runner, semantic graph, and Ibur. Stopped VMs
  211–218 also retain `.181`–`.188`, overlapping current guests. Do not boot
  these images with those identities on the live network.
- Seykhl retains stopped copies of Dolt, PostgreSQL, Dertog, runner-3, and
  sb-edge. The sb-edge copy is named `do-not-start`. Several stopped copies
  still have autostart enabled; a host reboot can revive old identities.
- The `g2` gate VMs run on Seykhl, but their PostgreSQL test containers run on
  Sefer's VLAN bridge. A name containing `g2` does not imply storage on Seykhl:
  Ibur (VM 130) also runs on Sefer.
- All 19 running test/experiment containers have PostgreSQL 16 `main` online
  on 5432. Their disks live on non-redundant `scratch`; none is in either
  configured Sefer VM backup job. Treat their data as disposable.
- All configured Sefer VM disks use mirrored storage, but production VMs 102,
  104 and 124 use raw files under `local` on the boot pool, not `vmdata`.

## QEMU guest agent availability

The VM configuration enables the agent throughout the running fleet, but
Sefer VMs 103, 104, 105, 107, 110, 111, 113, 114 and 116 reported that it was
not running. Their addresses and applications were inspected over SSH instead.
All other running VMs answered the network query. An enabled Proxmox setting
alone does not establish guest-agent availability or backup freeze/thaw.
