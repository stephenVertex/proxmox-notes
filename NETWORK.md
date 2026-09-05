# Host and guest networks

**Last verified:** 2026-09-05 from host interfaces, routing tables, VM bridge
configuration, and guest addresses. Physical connection roles were confirmed
by Stephen during the audit.

## Proxmox host access

| Host/interface | Address | Connection | Default route |
|---|---|---|---|
| Sefer `vmbr1` / `nic0` | `192.168.20.10/24` | VLAN 20, via SG108 on ER7206 port 5 | No gateway on this interface |
| Sefer `vmbr0` / `nic3` | `192.168.0.100/24` (DHCP) | Direct 10 GbE connection | `192.168.0.1` via `vmbr0` |
| Seykhl `vmbr0` / `nic0` | `192.168.20.202/24` (static) | VLAN 20 | `192.168.20.1` |

Both hosts participate in `192.168.20.0/24`. Sefer has two active physical
connections and retains its direct 10 GbE address. It has not moved exclusively
to VLAN 20. Seykhl no longer has `192.168.0.202` assigned.

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

## Guest placement

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

The complete observed guest addresses, bridges, and boot policies are in
[INVENTORY.md](INVENTORY.md). DHCP addresses and stale cloud-init values must
not be mistaken for router reservations; the router's lease/reservation table
was not audited.

## Read-only verification

```bash
ssh -o BatchMode=yes root@sefer 'ip -br -4 a; ip -4 route; cat /etc/network/interfaces'
ssh -o BatchMode=yes root@seykhl 'ip -br -4 a; ip -4 route; cat /etc/network/interfaces'
ssh -o BatchMode=yes root@sefer 'qm config 102; qm guest cmd 102 network-get-interfaces'
```

The hosts are separate standalone Proxmox installations, not members of one
cluster. VMIDs 100, 101, 102, 104, 110, 111, 113 and 231–238 overlap between
hosts. Always include both hostname and VMID in operational instructions.
