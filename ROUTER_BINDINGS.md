# ER7206 router bindings and cleanup

**Verified:** September 19, 2026; final cleanup snapshot
`2026-09-19T22:13:08.148Z`. This report covers the data-cleaning VM gateway
repairs and the subsequent requested cleanup of three obsolete camera/controller
bindings. It is a scoped router audit, not a new full fleet inventory.

The router's static **IP-MAC Binding** rules caused confirmed ARP-defense drops
even where its DHCP server was disabled. A free address in DNS/DHCP and a silent
duplicate-address probe did not reveal this persistent policy.

## Data-cleaning VM repairs

Four Debian 13 base VMs were created on **Seykhl**, using `vmbr0` with no guest
VLAN tag. Physical port placement puts them on Yesod/VLAN 20.

| VM | Name | Address | MAC |
| --- | --- | --- | --- |
| 700 | dataclean-postgres | 192.168.20.180 | 02:BD:C1:00:07:00 |
| 701 | dataclean-minio | 192.168.20.181 | 02:BD:C1:00:07:01 |
| 702 | dataclean-dagster | 192.168.20.182 | 02:BD:C1:00:07:02 |
| 703 | dataclean-api | 192.168.20.183 | 02:BD:C1:00:07:03 |

VMs 700, 701 and 703 could reach peers but could not reach the gateway or
internet. Router logs confirmed drops against these old bindings:

| Address | Previous MAC / owner | Corrected MAC / owner |
| --- | --- | --- |
| 192.168.20.180 | BC:24:11:B2:54:E4 / Sefer VM151 tzadik | 02:BD:C1:00:07:00 / Seykhl VM700 |
| 192.168.20.181 | BC:24:11:F7:DB:CE / Sefer VM233 ashmedai | 02:BD:C1:00:07:01 / Seykhl VM701 |
| 192.168.20.183 | BC:24:11:FF:BA:09 / Sefer CT244 lilith | 02:BD:C1:00:07:03 / Seykhl VM703 |

Those three records were corrected to the new MACs and labels, and their
interface changed from **LAN** to **Yesod**. VM702 had no conflicting binding.
The former Sefer VMs 151 and 233 were stopped; CT244 was live at
`192.168.0.183`. Their configurations and states were preserved.

All four new VMs passed direct SSH, QEMU guest agent, both DNS resolvers,
peer/gateway connectivity, external HTTPS 200, Chrony and configuration
persistence checks before and after reboot. The base-infrastructure bead
`btdcv1-26f.1` is closed. Application installation has not started and the extra
data disks remain blank.

Exact old/new records and router log samples are in
[VM binding corrections](evidence/router-2026-09-19/vm-binding-corrections.json).

## Camera and controller cleanup

The following three obsolete static ARP bindings were removed at Stephen's
request. Their prior interface was **LAN** and all three were enabled.

| Address | Previous MAC | Previous label |
| --- | --- | --- |
| 192.168.0.118 | EC:71:DB:BF:D6:71 | Garage Cam RLC-510a |
| 192.168.0.192 | BC:24:11:CF:6E:EC | yesod-runner-g1-dispatch controller (Sefer VM152) |
| 192.168.20.192 | BC:24:11:CF:6E:EC | yesod-runner-g1-dispatch controller (Sefer VM152) |

The camera at `192.168.40.118` returned both ping probes before and after
removal. Both current controller service addresses returned both probes after
removal. Reopening the router page confirmed the deletions persisted.

The live controller is **Sefer VM175**, `yesod-controller-g1-6c2a`:

| Guest interface | Host bridge / network | MAC | Addresses |
| --- | --- | --- | --- |
| eth0 | vmbr1 / Yesod | BC:24:11:DB:B3:59 | 192.168.20.58/24; service alias 192.168.20.192/32 |
| g1-compat | vmbr0 / trusted LAN | 02:59:05:00:01:75 | service alias 192.168.0.192/32 |

The router dynamically learned `192.168.0.192` as `02:59:05:00:01:75` on LAN
after cleanup. The old controller VM152 was stopped; its MAC no longer owns
these service addresses. Guest addresses and configurations were unchanged.

### Phone observation and limits

DHCP had leased `192.168.0.118` to `62:0D:DE:EC:BC:B0` while the old static
binding expected the camera MAC. Router logs confirmed ARP drops for that
client. This establishes a DHCP/ARP-policy conflict; it does not establish
that two live devices simultaneously used the address.

Stephen subsequently reported his phone working at `.119`, consistent with
avoiding the conflicting `.118` binding. The earlier client MAC was not proven
to belong to the phone. No forced renewal or reassignment to `.118` was tested,
and the observations do not establish the cause of every Wi-Fi problem.
Router log times are as displayed; its timezone was not independently verified.

## Preserved policy and DHCP ownership

After the three removals, **all 31 retained bindings, all six ACL entries and
all 53 router DHCP reservations matched the pre-cleanup configuration**.
ARP defense remains enabled; "Permit packets matching binding entries only"
is off. MAC filtering was observed off. General ARP settings were unchanged.

VLAN 20 DHCP moved to **Seykhl dnsmasq on September 13**. Its active file is
`/etc/dnsmasq.d/20-yesod-lan-dhcp.conf`, with pool
`192.168.20.20` through `192.168.20.119`.
The repository source retains the historical name
`dns/phase2-dhcp.conf.staged`. Sefer remains DNS-only. Router DHCP is disabled
for Yesod and enabled for LAN, iDRAC and Cameras. See [LAN_DNS.md](LAN_DNS.md).

The router still has historical reservations for `.20.180`, `.20.181` and
`.20.183` with the old MACs. These are inactive because its Yesod DHCP server
is disabled; the active reservations are on Seykhl. Do not reactivate router
DHCP using this stale table. Disabling DHCP does not disable ARP enforcement.

The separate old-controller DHCP reservations at `.0.192` and `.20.192` were
retained to guard against automatic address reuse. Reconcile their ownership
through the controller's service-address lifecycle before changing them.
Removing a static ARP binding does not remove a DHCP reservation.

## Remaining bindings on the trusted subnet

Only these three static bindings remain in `192.168.0.0/24`; all are enabled
and name the LAN interface. Labels are copied from the router, not newly
verified ownership claims.

| Address | MAC | Router label | Ownership context |
| --- | --- | --- | --- |
| 192.168.0.137 | BC:24:11:5E:D5:A8 | sb-edge | Sefer VM111 in the September 5 inventory |
| 192.168.0.172 | BC:24:11:B8:5D:94 | Reserved-172 | Matches the semantic graph VM121 MAC and the retained .20.172 binding |
| 192.168.0.218 | B8:CA:3A:63:0D:40 | Sefer 10gbe | Historical label; the September 5 host audit observed Sefer at .0.100 |

The [semantic graph service record](YESOD_SEMANTIC_GRAPH.md) places VM121 at
`.0.172` with this MAC. The router also has a `.20.172` rule labelled
`yesod-semantic-graph (Yesod VLAN 20, VM121)`. Recheck its live placement before
deciding which record is obsolete. The `.0.218` ownership also needs checking.
Stephen reconfirmed on September 19 that Sefer intentionally retains its
trusted-LAN connection for fast access to the NAS, Homestar. The question is
whether the `.0.218` rule matches that interface's current address and MAC;
the connection itself is expected. None of these three bindings was removed
in this cleanup.

## Address allocation and troubleshooting

Before reusing an address:

1. Check live and stopped guest configurations and MACs on **both standalone
   hypervisors**; identify guests by host and VMID together.
2. Check active DHCP reservations and leases, including which server owns the
   scope, and compare the DNS source with answers from both resolvers.
3. Inspect the router's **IP-MAC Binding**, **ARP List** and **Address
   Reservation** tables, including historical reservations on disabled scopes.
4. Probe for a live duplicate address. A silent probe alone does not rule out
   a stopped guest or persistent router policy.
5. If peers work but the gateway fails, compare the guest MAC with router
   bindings and look for matching ARP-defense drops. Validate a targeted repair
   with gateway, DNS and HTTPS checks before and after reboot.

Follow-up bead **`proxmox-bog`** tracks the remaining binding audit and controller
reservation reconciliation. Many retained VLAN 20 bindings still name LAN;
the camera's `.40.118` binding also says LAN despite its Cameras address.
Camera reachability passed. These mismatches are audit candidates, not proof
that every such rule is broken or permission to remove them in bulk.

## Recovery and evidence

The tables and JSON retain the previous MACs, labels and interfaces for
recovery review. Reinstating obsolete bindings would restore the identified
conflicts; first verify current address ownership. No global firewall,
DHCP-service or guest-network changes accompanied the targeted cleanup.

Local evidence copies are byte-identical to the data-cleaning project's
commit `88def23`:

- [VM binding corrections](evidence/router-2026-09-19/vm-binding-corrections.json)
- [Cleanup, retained rules and verification](evidence/router-2026-09-19/stale-binding-cleanup.json)
- [Source incident observations](https://github.com/stephenVertex/braintrust-dataclean-expert-test-alpha/blob/88def23/infra/evidence/network-followup.md)
- [Source base-VM acceptance before and after reboot](https://github.com/stephenVertex/braintrust-dataclean-expert-test-alpha/blob/88def23/infra/evidence/base-vms.json)
- [Source bootstrap recovery](https://github.com/stephenVertex/braintrust-dataclean-expert-test-alpha/blob/88def23/infra/evidence/bootstrap-recovery.md)

The complete retained rule inventory follows. It records the verified snapshot;
it does not certify every historical label, interface or IP-group membership.

## Current access-control rules

All six remain as observed; their IP-group memberships were not expanded.

| Order | Rule | Action | Service | Source | Destination |
| --- | --- | --- | --- | --- | --- |
| 1 | Yesod_NAS_RPCBIND | Allow | RPCBIND | IPGROUP_YESOD | IPGROUP_NAS |
| 2 | Yesod_NAS_MOUNTD | Allow | MOUNTD | IPGROUP_YESOD | IPGROUP_NAS |
| 3 | Yesod_NAS_NFS | Allow | NFS | IPGROUP_YESOD | IPGROUP_NAS |
| 4 | Yesod_NAS_ICMP | Allow | ICMP_ALL | IPGROUP_YESOD | IPGROUP_NAS |
| 5 | Yesod_TAILSCALE_41641 | Allow | TAILSCALE | IPGROUP_YESOD | IPGROUP_LAN |
| 6 | Yesod_DENY_TRUSTED_NEW | Block | ALL | IPGROUP_YESOD | IPGROUP_LAN |

## Remaining static ARP bindings

This is an inventory of retained rules, not a claim that every historical entry has been audited. All are enabled.

| IP | MAC | Interface | Label |
| --- | --- | --- | --- |
| 192.168.0.137 | BC-24-11-5E-D5-A8 | LAN | sb-edge |
| 192.168.0.218 | B8-CA-3A-63-0D-40 | LAN | Sefer 10gbe |
| 192.168.0.172 | BC-24-11-B8-5D-94 | LAN | Reserved-172 |
| 192.168.20.154 | BC-24-11-6C-CF-B7 | LAN | seykhl-actions-runner (Yesod VLAN 20) |
| 192.168.20.172 | BC-24-11-B8-5D-94 | LAN | yesod-semantic-graph (Yesod VLAN 20, VM121) |
| 192.168.20.167 | BC-24-11-B6-A5-A4 | LAN | neo4j (Yesod VLAN 20, VM118) |
| 192.168.20.173 | BC-24-11-38-A5-B3 | LAN | yesod-runner-g2-ibur (Yesod VLAN 20, VM130) |
| 192.168.20.136 | BC-24-11-68-88-B3 | LAN | yesod-runner-3 (Yesod VLAN 20, VM110) |
| 192.168.20.180 | 02-BD-C1-00-07-00 | Yesod | dataclean-postgres (Seykhl VM700) |
| 192.168.20.189 | BC-24-11-51-27-B3 | Yesod | lamedvov (Sefer VM150) |
| 192.168.20.157 | BC-24-11-85-BD-D3 | Yesod | litellm-gateway (Sefer VM101) |
| 192.168.20.163 | BC-24-11-C5-6C-AA | Yesod | obs-vultr SigNoz (Sefer VM117) |
| 192.168.20.185 | BC-24-11-87-26-9C | LAN | yesod-gate-g1-golem (Sefer VM131) |
| 192.168.20.178 | BC-24-11-ED-E9-BF | LAN | yesod-gate-g1-samael (Sefer VM231) |
| 192.168.20.176 | BC-24-11-5B-1C-FD | LAN | yesod-gate-g1-dybbuk (Sefer VM232) |
| 192.168.20.181 | 02-BD-C1-00-07-01 | Yesod | dataclean-minio (Seykhl VM701) |
| 192.168.20.196 | BC-24-11-13-77-FB | LAN | yesod-gate-g1-lilith (Sefer VM234) |
| 192.168.20.175 | BC-24-11-10-7D-E4 | LAN | yesod-gate-g1-azazel (Sefer VM235) |
| 192.168.20.194 | BC-24-11-CE-54-2C | LAN | yesod-gate-g1-estrie (Sefer VM236) |
| 192.168.20.188 | BC-24-11-92-2A-C8 | LAN | yesod-gate-g1-broxa (Sefer VM237) |
| 192.168.20.179 | BC-24-11-44-1A-53 | LAN | yesod-gate-g1-mazik (Sefer VM238) |
| 192.168.20.184 | BC-24-11-06-85-8D | LAN | test-db-g1-golem (Sefer CT220) |
| 192.168.20.190 | BC-24-11-E1-15-43 | LAN | test-db-g1-samael (Sefer CT241) |
| 192.168.20.195 | BC-24-11-FB-FB-1A | LAN | test-db-g1-dybbuk (Sefer CT242) |
| 192.168.20.197 | BC-24-11-31-A3-91 | LAN | test-db-g1-ashmedai (Sefer CT243) |
| 192.168.20.183 | 02-BD-C1-00-07-03 | Yesod | dataclean-api (Seykhl VM703) |
| 192.168.20.187 | BC-24-11-EA-E6-DF | LAN | test-db-g1-azazel (Sefer CT245) |
| 192.168.20.121 | BC-24-11-57-96-70 | LAN | test-db-g1-estrie (Sefer CT246) |
| 192.168.20.124 | BC-24-11-22-64-E3 | LAN | test-db-g1-broxa (Sefer CT247) |
| 192.168.20.127 | BC-24-11-D2-8A-9B | LAN | test-db-g1-mazik (Sefer CT248) |
| 192.168.40.118 | EC-71-DB-BF-D6-71 | LAN | --- |

