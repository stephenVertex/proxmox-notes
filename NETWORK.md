# Host and guest networks

**Full network audit:** 2026-09-05 from host interfaces, routing tables, VM bridge
configuration, and guest addresses. Physical connection roles were confirmed
by Stephen during the audit.

**Scoped update, 2026-09-19:** four data-cleaning base VMs on Seykhl passed
network checks before and after reboot. Three obsolete VM ARP bindings were
corrected and three camera/controller bindings removed from the ER7206. See
[router repairs, remaining rules and allocation guidance](ROUTER_BINDINGS.md).
The host and older guest tables below retain their September 5 audit scope.

## Proxmox host access

| Host/interface | Address | Connection | Default route |
|---|---|---|---|
| Sefer `vmbr1` / `nic0` | `192.168.20.10/24` | VLAN 20, via SG108 on ER7206 port 5 | No gateway on this interface |
| Sefer `vmbr0` / `nic3` | `192.168.0.100/24` (DHCP) | Direct 10 GbE connection | `192.168.0.1` via `vmbr0` |
| Seykhl `vmbr0` / `nic0` | `192.168.20.202/24` (static) | VLAN 20 | `192.168.20.1` |

Both hosts participate in `192.168.20.0/24`. Sefer has two active physical
connections and retains its direct 10 GbE address. It has not moved exclusively
to VLAN 20. Seykhl no longer has `192.168.0.202` assigned.

Sefer's trusted-LAN connection is intentional: Stephen reconfirmed on September
19 that it provides fast access to the NAS, Homestar. The retained router rule
labelled `Sefer 10gbe` at `.0.218` has not been reconciled with the `.0.100`
address observed in the host audit; it does not establish a second live address
or justify removing the trusted connection.

Use `https://192.168.20.10:8006` for Sefer and
`https://192.168.20.202:8006` for Seykhl. Sefer's direct-side UI remains at
`https://192.168.0.100:8006`. SSH aliases may still resolve to the direct side;
an explicit IP makes the intended path clear:

```bash
ssh -o BatchMode=yes root@192.168.20.10
ssh -o BatchMode=yes root@192.168.20.202
```

The live bridge configuration has no Linux VLAN subinterface or guest `tag=20`
setting. VLAN placement is provided by the physical switch/router ports.
Sefer's two bridges must not be treated as interchangeable.

## Guest placement (September 5 snapshot)

| Network | Host bridge | Current workloads |
|---|---|---|
| `192.168.20.0/24` | Sefer `vmbr1` | PostgreSQL 102, Dertog 104, Dolt 124, g2 test databases 251–259 |
| `192.168.20.0/24` | Seykhl `vmbr0` | g2 gate VMs 231–239; stopped legacy guests/templates are attached here too |
| `192.168.0.0/24` | Sefer `vmbr0` | Remaining running service/runner/g1 gate VMs and containers 141, 220, 241–248 |

The important changed guest endpoints are:

| Service | Current guest IPv4 | Previous guest IPv4 | Tailscale IPv4 |
|---|---|---|---|
| Dolt primary, Sefer VM 124 | `192.168.20.150` | `192.168.0.150` | `100.101.145.38` |
| PostgreSQL, Sefer VM 102 | `192.168.20.155` (DHCP at audit) | `192.168.0.155` | `100.115.10.68` |
| Dertog, Sefer VM 104 | `192.168.20.138` (DHCP at audit) | `192.168.0.138` | `100.64.95.60` |

PostgreSQL now listens on all guest interfaces, including the VLAN and
Tailscale endpoints. Consult [YESOD_POSTGRES_SERVER.md](YESOD_POSTGRES_SERVER.md)
for the verified listeners and HBA rules. Static `/etc/hosts`
and SSH entries using the previous LAN addresses need updating on each client.
The administrator Mac's three SSH aliases still pointed to the old addresses
when inspected; this documentation audit did not edit workstation networking.

The September 5 observed guest addresses, bridges, and boot policies are in
[INVENTORY.md](INVENTORY.md). DHCP addresses and stale cloud-init values must
not be mistaken for router reservations. The September 19
[router audit](ROUTER_BINDINGS.md) records the later scoped inspection of
bindings, leases and reservations, including historical entries still present.

## Name resolution

**Updated 2026-09-19.** LAN DNS runs on Seykhl at `192.168.20.202` and Sefer
at `192.168.20.10`, authoritative for `internal.yesod.work`, serving VLAN 20
and the trusted LAN. VLAN 20 DHCP moved to Seykhl dnsmasq on September 13;
Sefer remains DNS-only and the ER7206's Yesod DHCP server is disabled.
Seykhl supplies the resolver and search-domain options. Router ARP bindings
still apply independently of its DHCP setting.

This replaces the previous situation, in which the router forwarded DNS but
served no LAN names, and cross-VLAN resolution was impossible: mDNS `.local`
never crosses a VLAN and MagicDNS only covers tailnet members. Static
`/etc/hosts` pins should be retired in favour of names as hosts are touched.

Note that `sefer` resolves to `192.168.20.10`, the VLAN 20 side, because that
address is reachable from both segments; `sefer-trusted` is the direct 10 GbE
address. This mirrors the bridge warning above — the two paths are not
interchangeable.

Full configuration, verification commands and DHCP handover history are in
[LAN_DNS.md](LAN_DNS.md).

## Read-only verification

```bash
ssh -o BatchMode=yes root@sefer 'ip -br -4 a; ip -4 route; cat /etc/network/interfaces'
ssh -o BatchMode=yes root@seykhl 'ip -br -4 a; ip -4 route; cat /etc/network/interfaces'
ssh -o BatchMode=yes root@sefer 'qm config 102; qm guest cmd 102 network-get-interfaces'
```

The hosts are separate standalone Proxmox installations, not members of one
cluster. VMIDs 100, 101, 102, 104, 110, 111, 113 and 231–238 overlap between
hosts. Always include both hostname and VMID in operational instructions.
