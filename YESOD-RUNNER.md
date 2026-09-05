# Yesod runner and gate fleet

**Last verified:** 2026-09-05, from both Proxmox hosts and running guests.

## Current placement

The fleet now spans Sefer and Seykhl. The old three-runner description is
obsolete: Seykhl's VMs 106 and 108 are stopped, and runner-3 has moved to
Sefer. Gate VMs and their PostgreSQL test containers are separate guests.

| Host / VM | Name | Observed IPv4 | vCPU / RAM / disk |
|---|---|---|---|
| Sefer 110 | `yesod-runner-3` | `192.168.0.136` | 44 / 64 GiB / 160 GiB |
| Sefer 130 | `yesod-runner-g2-ibur` | `192.168.0.173` | 4 / 16 GiB / 160 GiB |
| Sefer 131 | `yesod-gate-g1-golem` | `192.168.0.185` | 36 / 48 GiB / 160 GiB |
| Sefer 150 | `yesod-runner-g1-lamedvov` | `192.168.0.189` | 4 / 16 GiB / 160 GiB |
| Sefer 151 | `yesod-runner-g1-tzadik` | `192.168.0.180` | 4 / 16 GiB / 160 GiB |
| Sefer 152 | `yesod-runner-g1-dispatch` | `192.168.0.192` | 4 / 8 GiB / 160 GiB |
| Sefer 231–238 | Eight g1 gates | See inventory | Each 8 / 8 GiB / 64 GiB |
| Seykhl 231–239 | Nine g2 gates | VLAN 20; see inventory | Each 4 / 7 GiB / 64 GiB |

All listed VMs were running. Sefer's fleet disks use mirrored `vmdata`;
Seykhl uses `local-lvm`. These runner/gate VMs have manual start policy
(`onboot=0` or omitted). Guest agent queries work except on runner-3.

**Host interfaces:** Sefer has VLAN `192.168.20.10` and separate direct
10 GbE `192.168.0.100`. Seykhl is `192.168.20.202`. Sefer g1 gates use its
`vmbr0`; Seykhl g2 gates use its `vmbr0`, which is on VLAN 20. See
[NETWORK.md](NETWORK.md) and [INVENTORY.md](INVENTORY.md) for the full mapping.

## Gate/database pairs

Each listed PostgreSQL test container was running PostgreSQL 16 `main` on
5432 when inspected. All of them are on Sefer, including the g2 databases
used with the gates on Seykhl.

| Gate | g1 VM on Sefer | g1 database CT on Sefer | g2 VM on Seykhl | g2 database CT on Sefer |
|---|---:|---:|---:|---:|
| samael | 231 | 241 | 231 | 251 |
| dybbuk | 232 | 242 | 232 | 252 |
| ashmedai | 233 | 243 | 233 | 253 |
| lilith | 234 | 244 | 234 | 254 |
| azazel | 235 | 245 | 235 | 255 |
| estrie | 236 | 246 | 236 | 256 |
| broxa | 237 | 247 | 237 | 257 |
| mazik | 238 | 248 | 238 | 258 |
| golem | 131 | 220 | 239 | 259 |

Pairing here follows matching deployed guest names; active application routing
was not independently audited. The g1 database containers use Sefer `vmbr0`;
g2 containers use Sefer `vmbr1` on VLAN 20. CT 220 has 8 vCPU/8 GiB; CTs
241–248 and 251–259 have 4 vCPU/4 GiB. Each has a 16 GiB disk on
**non-redundant `scratch`**. CT 141 `hosted-experiment-pg16` is a separate
2-vCPU/2-GiB/16-GiB PostgreSQL 16 experiment on the same storage.

The gate VMs retain guest-native PostgreSQL 17 installations whose `main`
clusters are down; this is distinct from the online PostgreSQL 16 test
containers. Do not label all of those stopped guest clusters as production
outages or start them merely because they are installed.

## Application services observed

The service snapshots below were taken while PostgreSQL repairs were in
progress. They are observations, not a permanent declaration of worker health
or proof of which workers are registered in the application database. Ibur
and the main dispatcher recovered during the operator's PostgreSQL repairs;
the final recheck below supersedes their initial restart-loop observations.

| VM | Observation |
|---|---|
| runner-3, Sefer 110 | `yesod-codefactory-dispatch` inactive; native PostgreSQL 17.11 active; archive-sweep unit failed |
| Ibur, Sefer 130 | Final recheck: dispatch active/running, `NRestarts=0`; Caddy active |
| Lamedvov, Sefer 150 | Dispatch active; `litellm-local-proxy` failed; several retained experimental transient units failed |
| Tzadik, Sefer 151 | Caddy active; no active dispatch unit in the initial loaded-unit listing |
| Dispatch, Sefer 152 | Final recheck: dispatch and refinery active/running, `NRestarts=0`; earlier beads-collect failure retained |
| g1/g2 gates | Guests reachable through QEMU agent; no active persistent dispatch service in the initial loaded-unit listing |

A gate may run on-demand jobs without a persistent dispatcher. No job was
submitted, no registered worker inventory was queried, and no idle guest was
started. Use application-side worker/job evidence before assigning capacity.
Retained failed one-shot experiments are not by themselves current fleet faults.

## Runtime paths and access

Current newer guests contain `/srv/yesod` and `/opt/yesod`. The dispatch unit
path remains `/etc/systemd/system/yesod-codefactory-dispatch.service`; Sefer
VM 152 also has `yesod-refinery-controller.service`. Dertog runs the Yesod
HTTP API and live visualization separately; see [DERTOG.md](DERTOG.md).

Database endpoint configuration must match the current PostgreSQL server,
not the old `192.168.0.155` value. The live VLAN endpoint is
`192.168.20.155:5432`; Tailscale remains `100.115.10.68:5432`. Do not print
runner environment files or DSNs containing credentials. See
[YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md) for current listener and
access-rule details. LiteLLM's deployed gateway is documented in
[LITELLM_GATEWAY.md](LITELLM_GATEWAY.md).

```bash
ssh -o BatchMode=yes stephen@192.168.0.173 \
  'systemctl show yesod-codefactory-dispatch -p ActiveState -p SubState -p NRestarts -p Result'
ssh -o BatchMode=yes root@sefer 'qm guest exec 152 -- systemctl is-active yesod-refinery-controller'
ssh -o BatchMode=yes root@seykhl 'qm guest cmd 231 network-get-interfaces'
ssh -o BatchMode=yes root@sefer 'pct exec 251 -- pg_lsclusters'
```

Review active work before restarting any controller or runner. A momentary
`is-active` result can hide a restart loop; inspect restart count and logs.

## Templates and retained copies

Sefer has templates 9000 (`yesod-runner-template`, 8 vCPU/24 GiB/64 GiB),
9100 (`yesod-node-template`, 8 vCPU/8 GiB/64 GiB), 9101
(`yesod-gate-g1-unborn`, 8 vCPU/8 GiB/64 GiB), and PostgreSQL CT templates
9010/9011. Seykhl retains the older runner base 109, gate template 9101 and
CT template 9011. Current g1 linked clones reference both 9100 and 9101;
test databases likewise reference both 9010 and 9011. Preserve template disks
while dependent linked clones exist.

Seykhl's old runners 106/108/110 and dispatcher 112 are stopped. VMs 106,
108 and 112 still have autostart enabled. Sefer VMs 201–203 and 211–218 are
stopped older runner/gate images; their retained static IPs overlap live
services. See [INVENTORY.md](INVENTORY.md#configuration-cautions) before any
boot or clone. Old setup commands and model/auth configurations from the
June three-runner deployment remain in git history, not as current runbooks.

## Backup boundary

The expanded Yesod runner/gate fleet is absent from both current Sefer
scheduled backup jobs. Seykhl has no Proxmox scheduled job file. The disposable
PostgreSQL containers must not hold the sole copy of durable application data.
See [BACKUPS.md](BACKUPS.md) for the separate production database and backup
coverage audit.
