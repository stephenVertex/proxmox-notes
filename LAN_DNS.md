# LAN DNS and DHCP (dnsmasq on Seykhl + Sefer)

**Original DNS verification:** 2026-09-10 from the running services on both hosts, the
ER7206 web UI, live resolution tests executed on gate demons on both VLANs, and
a failover test with the primary resolver stopped. Scoped DHCP, new-VM and
router-binding updates are recorded in the September 19 section below.

> **Interim by design.** This service exists because the fleet had no LAN name
> resolution and a names-only contract began to fail closed. It is expected to
> be **folded into yesod itself** eventually — the inventory in
> `/etc/yesod/dns/infra.hosts` is a hand-curated file today and is the obvious
> thing for yesod to render from its own catalogue. Treat the file as the
> temporary source of truth, not the permanent design. See
> [Folding into yesod](#folding-into-yesod).

## Current state verified 2026-09-19

VLAN 20 DHCP is now **active on Seykhl**, using
`/etc/dnsmasq.d/20-yesod-lan-dhcp.conf`; Sefer remains DNS-only. The September 13
handover supersedes the historical staged-only statements below. Do not enable
a second DHCP server on the router. The pool is still `.20`–`.119`. The repository
source retains the historical filename `dns/phase2-dhcp.conf.staged`.

Completed bead `btdcv1-26f.1` added four durable data-cleaning base VMs on Seykhl:

| VM | Name | Address | MAC |
| --- | --- | --- | --- |
| 700 | dataclean-postgres | 192.168.20.180 | 02:BD:C1:00:07:00 |
| 701 | dataclean-minio | 192.168.20.181 | 02:BD:C1:00:07:01 |
| 702 | dataclean-dagster | 192.168.20.182 | 02:BD:C1:00:07:02 |
| 703 | dataclean-api | 192.168.20.183 | 02:BD:C1:00:07:03 |

They use static guest addresses plus matching reservations, and names under
`internal.yesod.work` in `dns/infra.hosts` on both resolvers. The live `.192`
log-relay/controller record was preserved and reconciled into the repository.

The DHCP update preserved existing entries and the lease file, backed up the old
configuration, added only these four reservations, and passed `dnsmasq --test`.
`scripts/deploy-lan-dns.sh seykhl` and then `sefer` deployed DNS and reloaded the
services. This is maintenance of the active service, not `--activate-dhcp`.
The historical `dhcp` DNS alias still points to the router; that alias is not
proof of which machine currently serves leases.

Deployment scripts, image checksum, disk inventory, and reboot verification are
in [the data-cleaning project at 88def23](https://github.com/stephenVertex/braintrust-dataclean-expert-test-alpha/tree/88def23/infra).
All four base VMs passed acceptance before and after reboot; applications are
not installed and their extra data disks remain blank.

### Router bindings are separate from DHCP

Stale ER7206 ARP bindings blocked `.20.180`, `.20.181` and `.20.183` even with
router DHCP disabled on Yesod. Those three bindings now use the new VM MACs,
labels and Yesod interface. The later cleanup removed the obsolete camera
binding at `.0.118` and old-controller bindings at `.0.192` and `.20.192`.
All 31 remaining bindings, six ACL entries and 53 DHCP reservations were
preserved. ARP defense remains enabled; binding-only allowlisting is off.

Historical router reservations for the new VM addresses remain inactive.
The old-controller reservations remain to guard the service addresses against
automatic reuse; follow-up bead `proxmox-bog` tracks ownership reconciliation.
Do not re-enable the router's Yesod DHCP server using its old reservation table.

Before allocating an address, check active DHCP leases/reservations, DNS,
live and stopped guest ownership on both hosts, and the router's IP-MAC
Binding, ARP List and Address Reservation tables. A silent duplicate-address
probe cannot rule out stale router policy. See [ROUTER_BINDINGS.md](ROUTER_BINDINGS.md)
for exact changes, current rules, controller addresses and verification limits.

## Why this exists

The fleet relied on three name mechanisms, none of which covers the whole
estate:

| Mechanism | Covers | Cannot do |
|---|---|---|
| mDNS / avahi (`.local`) | hosts on the **same** VLAN | never crosses a VLAN boundary |
| Tailscale MagicDNS (`*.ts.net`) | tailnet **members** | gate demons and test databases are not members |
| `/etc/hosts` pins | whatever was written | rots the moment an address moves |

The ER7206 forwards DNS but serves no LAN names. The result, measured on
2026-09-10: a gate demon could resolve `sefer.local` (same VLAN, mDNS) but
**not** `seykhl`, `nas`, `router` or `gateway`. That is protocol behaviour, not
a misconfiguration.

This blocked real work. The dg5 fleet inventory contract requires names-only
endpoints and forbids literal IP addresses, yet it pinned NTP to the literal
name `seykhl`, which no demon could resolve. It worked only because the demons
pointed `timesyncd` at the raw `192.168.20.202` — exactly what the contract
forbids. Tracked as yesod note `ys-yes-81xu`.

## Where it runs

**dnsmasq 2.91 on BOTH Proxmox hosts**, alongside chrony on each. Seykhl is
the primary and Sefer the secondary (added 2026-09-10).

Seykhl was chosen as primary for the same reasons it hosts NTP: separate
physical machine, single NIC already on VLAN 20, stable across the guest
cutovers in progress on Sefer.

| Role | Host | Resolver address | NTP |
|---|---|---|---|
| Primary | Seykhl | `192.168.20.202` (`vmbr0`) | `ntp1` |
| Secondary | Sefer | `192.168.20.10` (`vmbr1`), also `192.168.0.100` (`vmbr0`) | `ntp2` |

**Sefer's bridges are the opposite way round from Seykhl's** — `vmbr1` is
VLAN 20 and `vmbr0` is the trusted LAN — which is exactly why the dnsmasq
config is split into a shared file and a per-host interface file rather than
copied. Sefer listens on both of its bridges on purpose: VLAN 20 clients use
it as their secondary, and the trusted segment gains a local resolver that
knows the internal zone (the router cannot answer `internal.yesod.work` at
all).

| Item | Value |
|---|---|
| Shared config | `/etc/dnsmasq.d/10-yesod-lan-common.conf` |
| Per-host interfaces | `/etc/dnsmasq.d/11-yesod-lan-iface.conf` |
| Host inventory | `/etc/yesod/dns/infra.hosts` (identical on both, checksum-verified) |
| Bind mode | `bind-dynamic`, restricted by `interface=`; **never** `tailscale0` |
| Active VLAN 20 DHCP (Seykhl only, since September 13) | `/etc/dnsmasq.d/20-yesod-lan-dhcp.conf`; repo source `dns/phase2-dhcp.conf.staged` |
| Resolvconf suppression | `IGNORE_RESOLVCONF=yes` in `/etc/default/dnsmasq` |
| Log | `/var/log/dnsmasq.log` |
| Unit state | `enabled`, `active`, `Restart=on-failure` on both |
| Chrony server config | `/etc/chrony/conf.d/yesod-lan-server.conf`, from `ntp/` |

**The repo is the source of truth, not the hosts.** All of the above is
deployed from `dns/` by `scripts/deploy-lan-dns.sh`; editing the files
directly on a host will be silently overwritten on the next deploy.

Trusted-LAN clients reach it directly because trusted → VLAN 20 is already
open and stateful, so no firewall change was required.

## Domain

Canonical: **`internal.yesod.work`**

Stephen owns `yesod.work`. Before committing to it we confirmed the subdomain
is safe to claim locally:

- `yesod.work` is Cloudflare-hosted (`asa`/`patryk.ns.cloudflare.com`)
- `internal.yesod.work` has **no** public records
- there is **no** wildcard on `yesod.work`

`local=/internal.yesod.work/` makes dnsmasq authoritative for that subdomain
only, so it is never forwarded and it shadows nothing. Verified after the
change: `yesod.work` itself still resolves through this resolver to its real
public Cloudflare addresses.

**`.local` was deliberately rejected** — it is reserved for mDNS and would
collide with the avahi resolution the demons already depend on.

Every host answers to four forms:

```
<name>.internal.yesod.work     canonical
<name>.lan.planetbarr.com      transitional alias, remove when unreferenced
<name>.lan                     short alias
<name>                         bare, via the DHCP-supplied search domain
```

The `lan.planetbarr.com` form is a **transitional alias only**. It was the
first build's domain and had already been sent to the factory mayor before the
domain was settled; it is kept so nothing already rendered breaks, and it
should be deleted once nothing references it.

## Upstream resolvers

```
server=1.1.1.1
server=9.9.9.9
server=/ts.net/100.100.100.100
```

**The gateway's unbound is deliberately not an upstream.** On 2026-09-04 it
produced three ~30-second resolution failures in 70 minutes that killed two
runner claims and one push of a finished commit (yesod note `ys-yes-ljwz`).
Going straight to public resolvers removes the gateway from that path for every
LAN client at once.

Forwarding `ts.net` to MagicDNS means tailnet names resolve for **every** LAN
client, not only tailnet members. Verified: `seykhl.tailb4b58.ts.net` →
`100.80.216.118`.

`no-resolv` is set because Tailscale owns `/etc/resolv.conf` on Seykhl and
points it at `100.100.100.100`; without it dnsmasq would forward its own
queries in a loop.

`no-hosts` is set because Seykhl's `/etc/hosts` says `seykhl.lan` and Sefer's
says `sefer.meshcrawler.com`. Both are Proxmox install artifacts and neither
should become fleet-wide truth.

## What is in the inventory, and what is deliberately absent

`/etc/yesod/dns/infra.hosts` holds **only** hosts that are long-lived *and*
stably addressed — 27 hosts, 140 names.

Ephemeral guests — gate demons, test databases, runners — are **deliberately
absent**. They live in the DHCP pool `192.168.20.20–.119`, are reborn into
whatever address the pool hands out, and once dnsmasq owns DHCP they register
their own names at lease time. Adding one by hand is the same mistake as giving
it a router reservation.

Selected entries:

| Name | Address | Note |
|---|---|---|
| `seykhl` | `192.168.20.202` | this host |
| `sefer` | `192.168.20.10` | **not** `192.168.0.100` — see below |
| `sefer-trusted` | `192.168.0.100` | the direct 10 GbE side |
| `nas`, `synology` | `192.168.0.123` | NFS only across the boundary |
| `router`, `gateway`, `gw` | `192.168.20.1` | ER7206, VLAN 20 side |
| `router-trusted` | `192.168.0.1` | ER7206, trusted side |
| `dns`, `ns`, `resolver` | `192.168.20.202` | this service, so it can be declared by name |
| `ntp` | `192.168.20.202` | chrony on Seykhl |
| `dhcp` | `192.168.20.1` | **moves to `.20.202` at phase 2** |
| `postgres`, `pg` | `192.168.20.155` | Sefer VM 102 |
| `doltsvr` | `192.168.20.150` | Sefer VM 124 |
| `dertog` | `192.168.20.138` | Sefer VM 104 |
| `litellm` | `192.168.20.157` | Sefer VM 101 |

**`sefer` resolves to the VLAN 20 address on purpose.** Sefer has two active
connections; `192.168.20.10` is reachable from *both* segments, while
`192.168.0.100` would resolve fine and then be firewall-blocked from VLAN 20. A
name that resolves and then fails is worse than no name. Use `sefer-trusted`
when the direct side is specifically wanted. This is the same trap as Sefer's
two bridges in [NETWORK.md](NETWORK.md) — the two paths are not
interchangeable.

## Router configuration (ER7206, September 10 history)

The following records the original DNS-option change. Since September 13,
the router's Yesod DHCP server has been disabled and Seykhl serves the scope;
these historical settings and rollback notes are not the current DHCP runbook.

Changed 2026-09-10 under `Network → LAN → Network List → Yesod (VLAN 20) → Edit`.
Values before the change: all four optional fields were **empty**, which is why
clients fell back to the router itself.

| Field | Before | After |
|---|---|---|
| Primary DNS | *(empty)* | `192.168.20.202` (Seykhl) |
| Secondary DNS | *(empty)* | `192.168.20.10` (Sefer) |
| Default Domain | *(empty)* | `internal.yesod.work` |

Unchanged: DHCP Mode `DHCP Server`, Status `Enable`, pool
`192.168.20.20`–`192.168.20.119`, Lease Time `120` minutes, Default Gateway
empty.

Both entries are real resolvers that know the internal zone. The secondary was
briefly `192.168.20.1` (the router itself) between the first and second edit on
2026-09-10, and that was a mistake worth naming: **the router cannot answer
`internal.yesod.work` at all**, so falling back to it would have turned a
dnsmasq outage into a subtler "internal names silently vanished" failure while
external DNS kept working. Once Sefer became a real second resolver the
secondary was repointed at `192.168.20.10`.

Caution when editing: the ER7206 web session expires quietly, and a save
submitted against an expired session redirects to the login page **without
applying the change**. Verify by asking a client what it actually received
(`dhclient` renew, then read `/etc/resolv.conf`) rather than trusting the form.

**The trusted LAN (VLAN 1, `192.168.0.1`) was not touched** and still runs its
own DHCP server. Phase 2 does not change that either — it moves VLAN 20 only.

Because the lease is 120 minutes, VLAN 20 hosts pick this up within roughly an
hour on their own renewal. No gate host had to be reconfigured, which also
respects the factory constraint that no gate host may be changed while an
attempt is `gating`.

**Rollback:** clear those three fields on the same page.

## How ephemeral guests get names

**Not by querying Proxmox.** The guest tells us.

A DHCP request carries the client's own hostname (option 12, or option 81 for
the FQDN). dnsmasq binds that name to the address it just issued and answers
DNS for it immediately. cloud-init already sets each guest's hostname at birth.

So a demon's name appears when it boots, follows it to whatever address it is
reborn into, and vanishes with the lease — no inventory file, no zone edit, no
reservation, no API call. Querying Proxmox would be the wrong answer: it puts a
second source of truth beside the one the guest already holds about itself.

Verified on `yesod-gate-dg5-ziz-b33d`: netplan `dhcp4: true` under
systemd-networkd with no `SendHostname` override, so the default (send it)
applies.

This requires dnsmasq to own DHCP, which became active on Seykhl on September
13. The original September 10 phase 1 was DNS-only. Sefer remains DNS-only.

## Phase 2 — investigated 2026-09-10 and NOT DONE (proxmox-7ik closed)

**Historical decision, superseded by the September 13 handover.** The following
rationale, staged settings and activation/rollback commands describe the
September 10 proposal. Use the current-state section for the active file and
DHCP owner; do not repeat this old activation sequence on the live system.

> **Decision: do not move DHCP off the router.** The config below stays staged
> and documented because it costs nothing to keep, but the case for running it
> did not survive investigation. Rationale first, then the mechanics in case a
> future requirement revives it.

### Why phase 2 was dropped

Its headline benefit was that ephemeral guests would get DNS names
automatically at lease time. Measured on 2026-09-10, that benefit has no
consumer:

| Claimed benefit | Reality |
|---|---|
| Ephemeral guests become resolvable by name | **Already true via mDNS inside VLAN 20.** From a dg5 demon, other demons and test databases resolve 4/4 by `.local`; the controller resolved 18/18 when it was on VLAN 20 |
| Avoids avahi name conflicts on restart (a real historical problem) | **Fixed by the dg5 suffix convention, not by DNS.** `yesod-gate-dg5-ziz-b33d` carries a random suffix, so collisions are structurally unlikely. Zero conflicts or withdrawals in the avahi journals of the demons checked |
| Router reservations become version-controlled text | **Moot.** Reservations for ephemeral hosts were retracted; the 19 legacy VLAN 20 rows are to be *deleted*, not migrated |
| Clients get DNS, search domain and NTP by DHCP | **Already delivered** by three fields on the router (see above) |
| No more router console trips for addressing | **Already true.** The only remaining router work is one-time deletions |

And the one consumer that genuinely sits across a VLAN boundary — the refinery
controller — is moving *onto* VLAN 20 by design. Its config contains zero
literal `192.168.20.x` addresses and eight `.local` references, so mDNS serves
it once it shares a segment with its demons. Nothing outside VLAN 20 needs to
resolve a demon by name.

### And the cost is real

Moving DHCP to dnsmasq makes **DHCP a single point of failure on Seykhl**.
dnsmasq cannot serve one pool redundantly from two hosts without splitting the
range and giving up shared lease state.

That matters more for this fleet than it would for pets. **These demons are
cattle — destroyed and reborn routinely** — and a newborn guest needs DHCP to
obtain any address at all. So if Seykhl were down, existing hosts would keep
their leases but *no demon could be born*. Having just removed exactly that
class of single point of failure for DNS and NTP, reintroducing it for DHCP is
a net regression.

Meanwhile the ER7206 is a purpose-built appliance at 249 days uptime, and the
pool is nowhere near pressure — 17 of 100 addresses in use, so none of
dnsmasq's finer allocation control is needed.

### What would revive it

- Something outside VLAN 20 needing to resolve ephemeral guests by name, which
  mDNS structurally cannot serve.
- Wanting DHCP reservations or per-host options that the ER7206 cannot express.
- Retiring the router's DHCP for an unrelated reason.

If any of those land, the staged config is ready and the mechanics below apply.

### The staged config, if it is ever needed

`/etc/yesod/dns/phase2-dhcp.conf.staged` moves VLAN 20 DHCP from the ER7206 to
dnsmasq. It is deliberately **outside** `/etc/dnsmasq.d/` so it cannot load by
accident.

What it does:

- pool `192.168.20.20–.119`, unchanged from the router's policy
- `dhcp-authoritative`, leases in `/var/lib/misc/dnsmasq.leases`
- hands out router, DNS (`.20.202` then `.20.1`), and domain-search options
- `option:ntp-server 192.168.20.202` — so time needs no per-host config, which
  is what lets the fleet inventory stop carrying a literal address
- `dhcp-fqdn`, so DHCP names land in DNS under the canonical domain
- **nine `dhcp-host` lines that replace the router's VLAN 20 reservations as
  version-controlled text**, editable without a router console

Ephemeral guests get no `dhcp-host` line and never should.

**Activation order matters:**

1. Disable the ER7206's DHCP server for VLAN 20. **This must happen first** —
   two DHCP servers on one L2 segment is worse than none.
2. `cp -f /etc/yesod/dns/phase2-dhcp.conf.staged /etc/dnsmasq.d/yesod-lan-dhcp.conf`
3. `dnsmasq --test && systemctl restart dnsmasq`
4. Verify a guest renews to the same address and its name resolves.

**Rollback:** `rm -f /etc/dnsmasq.d/yesod-lan-dhcp.conf`, restart dnsmasq,
re-enable DHCP on the router. Existing leases keep working throughout.

Note before activating: the staged file currently sets a 12h lease while the
router uses 120 minutes. Align it so the handover does not quietly change
behaviour.

## Read-only verification

Everything at once, from the workstation — checks both hosts, compares
inventory checksums, probes eight names on each, and confirms the public
parent domain is not shadowed:

```bash
cd ~/dev3/proxmox-exper && ./scripts/deploy-lan-dns.sh --check
```

Service and inventory, per host (`192.168.20.202` Seykhl, `192.168.20.10` Sefer):

```bash
ssh -o BatchMode=yes root@192.168.20.202 'systemctl is-active dnsmasq; systemctl is-enabled dnsmasq'
ssh -o BatchMode=yes root@192.168.20.202 'ss -lunp | grep -w 53; ss -lunp | grep -w 67'
ssh -o BatchMode=yes root@192.168.20.202 'dnsmasq --test; tail -5 /var/log/dnsmasq.log'
```

Resolution, from Seykhl:

```bash
dig +short @192.168.20.202 ntp.internal.yesod.work A     # 192.168.20.202
dig +short @192.168.20.202 -x 192.168.20.155             # yesod-postgres-server.internal.yesod.work.
dig +short @192.168.20.202 yesod.work A                  # real Cloudflare addresses, NOT shadowed
dig +short @192.168.20.202 seykhl.tailb4b58.ts.net A     # MagicDNS still works
```

**From a gate demon, use `host` — there is no `dig` and no `nslookup` on
them.** A cross-VLAN test once read as a total failure and was simply a missing
binary; tcp/53 was open the whole time.

```bash
ssh -o BatchMode=yes stephen@<demon> 'for n in ntp dns nas seykhl sefer postgres; do host -W2 "$n" 192.168.20.202; done'
```

Historical September 10 client pick-up check, after a renewal:

```bash
ssh -o BatchMode=yes root@sefer 'pct exec 260 -- sh -c "grep -v ^# /etc/resolv.conf; getent hosts ntp"'
```

Historical example (the router fallback shown here was subsequently replaced
by Sefer at `192.168.20.10`; current clients should receive both real resolvers):

```
domain internal.yesod.work
search internal.yesod.work
nameserver 192.168.20.202
nameserver 192.168.20.1
```

## Verified results, 2026-09-10

Resolution confirmed from `yesod-gate-dg5-ziz-b33d` (`192.168.20.90`, VLAN 20)
and from `yesod-gate-g1-lilith` (`192.168.0.196`) and `yesod-gate-g1-golem`
(`192.168.0.185`) on the trusted LAN — the cross-VLAN case mDNS structurally
cannot serve:

```
ntp -> 192.168.20.202     seykhl   -> 192.168.20.202     sefer    -> 192.168.20.10
dns -> 192.168.20.202     nas      -> 192.168.0.123      postgres -> 192.168.20.155
dhcp-> 192.168.20.1       router   -> 192.168.20.1        doltsvr  -> 192.168.20.150
```

Router pick-up confirmed end to end on CT 260 `test-db-dg4-ifrit-337c`
(deliberately an idle dg4 container, not a live gate). After a forced renewal it
kept `192.168.20.73` and received the new resolver, domain and search list.
Bare names then resolved with no FQDN and no explicit server, and external DNS
still worked.

## Redundancy (added 2026-09-10)

Seykhl was initially the only resolver *and* the only time source. That is now
fixed: Sefer runs a second dnsmasq and a second chrony server.

**DNS.** Both resolvers hold an identical inventory (checksum-compared by
`scripts/deploy-lan-dns.sh --check`) and answer independently — this is two
full copies, not a forwarder chain, so neither depends on the other. Clients
receive both via DHCP.

*Failover verified* by stopping dnsmasq on Seykhl and querying from
`yesod-gate-dg5-ziz-b33d`: the primary refused, `192.168.20.10` answered
`postgres` correctly, and the primary resumed on restart.

**NTP — corrected 2026-09-10 23:5xZ, do not reintroduce peer symmetry.**
Sefer was briefly configured as a **symmetric chrony peer** of Seykhl so that
neither depended on the other. That was wrong for two reasons the fleet mayor
caught:

1. The gate birth attestor (`ops/gate/attest-host-time.py`) matches chrony's
   **server** marker `^*` only. A symmetric peer renders as `=` and can never
   match, so every gate and testdb birth on Sefer would fail with *"chrony did
   not select exactly one seykhl network source"*.
2. Far worse, with the Debian pool still present chrony **actually selected a
   public internet server and left Seykhl unselected**, and it flapped.
   Measured before the fix:

   ```
   ^* ntps2-01.bji01.0150n.net     2  ...   <- selected, PUBLIC internet
   =+ seykhl.internal.yesod.work   3  ...   <- reviewed source, NOT selected
   ```

   Sefer's clock gates every birth, so it was being steered by a stranger.

**The fix: Sefer follows Seykhl in client mode, and the alternative is absent
rather than demoted.** `prefer` only biases selection — chrony can still pick a
pool source when the preferred one is briefly unreachable, which is exactly the
flapping above.

```
# sefer: /etc/chrony/conf.d/yesod-lan-server.conf
server 192.168.20.202 iburst prefer
# sefer: /etc/chrony/chrony.conf
# pool 2.debian.pool.ntp.org iburst      <- commented out, backup kept
```

The matching `peer` line was also removed from Seykhl; leaving it would have
kept a symmetric association alive from the other side. The chain is now
unambiguous:

```
public pool -> seykhl (root, stratum 2) -> sefer (stratum 3) -> fleet
```

Verified: exactly one line of Sefer's `chronyc sources` matches the attestor's
regex, and it is Seykhl. No `=` associations remain anywhere.

**Sefer's chrony names Seykhl by literal IP, deliberately.** Time must not
depend on DNS at boot, and DNS on that host now depends on its own dnsmasq
starting — a name there would be a loop waiting to happen.

**What this costs, stated plainly:** it converts two independent sources into
one root plus a relay. That is accepted because **serving and following are
different roles**. Sefer still answers `ntp2` for the fleet and still carries
`local stratum 10`, so it keeps serving last-known time if Seykhl dies —
verified, both respond to real NTP queries from a VLAN 20 client. But a host
whose clock gates births should **fail closed**: with no upstream there is no
`^*`, so births refuse rather than minting demons against an unreviewed clock.
A public fallback that silently took over would defeat the purpose of attesting
time at all — the same fail-closed argument as the
`local=/lan.planetbarr.com/` guard.

**Naming.** `dns1`/`ntp1` are Seykhl, `dns2`/`ntp2` are Sefer.

> **`ntp.internal.yesod.work` MUST resolve to exactly ONE address.** This is a
> hard constraint, not a preference. The birth attestor raises
> `AttestationError("... must resolve uniquely to ...")` if the name returns
> more than one address, so a round-robin there would break **every birth and
> every attestation fleet-wide** — while looking like a DNS improvement.
> Recorded here because it was nearly done: a multi-valued `ntp` was about to
> be proposed so the second time source could be used without a code change,
> and the mayor's constraint arrived first.
>
> The redundancy that matters lives at the *serving* layer, which `ntp1`/`ntp2`
> already provide. The attested birth path is single-rooted by design.

The bare `dns` name likewise resolves to Seykhl only, since the dg5 inventory
was validated against it.

**Both services are crash-safe as well as reboot-safe.** Debian ships dnsmasq
and chrony with `Restart=no`, meaning a single failed bind at boot or any later
crash would leave the service silently dead — worst of all on the *secondary*,
where nobody would notice until the primary also failed. Both now carry a
drop-in with `Restart=on-failure`, `RestartSec=2s` and
`StartLimitIntervalSec=0` (keep retrying rather than giving up after a burst).
Verified with `kill -9` on dnsmasq: systemd restored it with a new PID inside
six seconds.

`bind-dynamic` replaced `bind-interfaces` plus a hardcoded `listen-address` for
the same reason — the old form required the address to already exist at
startup, so a bridge coming up a moment late at boot meant a permanent failure.

## Known gaps
- **The inventory is hand-curated.** It lives in the repo at `dns/infra.hosts`
  and is deployed to both hosts, so the two cannot drift from each other — but
  it can still drift from reality as guests move. See below.
- **Controller ownership still needs reconciliation.** The `.20.192`
  log-relay/controller DNS record is present as of September 19. Current VM175
  owns both `.20.192` and the trusted compatibility alias `.0.192`; old VM152
  DHCP reservations remain. See [the router report](ROUTER_BINDINGS.md) and
  follow-up bead `proxmox-bog` before changing these service-address records.
- **The g1 demons** resolve through this server but still take `192.168.0.1`
  from the trusted DHCP scope. They are being retired, so this is not worth a
  router edit.
- **`lan.planetbarr.com`** aliases remain until confirmed unreferenced.

## Folding into yesod

The intent is for yesod to own this. The pieces that should move:

1. **The inventory.** `infra.hosts` duplicates knowledge yesod already has
   about which services exist and where. yesod should render the file (or serve
   the zone directly) from its catalogue, so a service moving address updates
   DNS without a hand edit. This is the main reason the current file is
   explicitly labelled temporary.
2. **The reservation list.** Phase 2's `dhcp-host` lines are the router's
   reservation table in text. They encode the policy "long-lived *and* reached
   by literal address" and yesod is the natural place for that judgement to
   live.
3. **The policy itself.** The rule that ephemeral hosts get neither a
   reservation nor a hand-written record is a fleet invariant, not a dnsmasq
   detail.

Until then this document and the two files on Seykhl are the source of truth.

## See also

- [NETWORK.md](NETWORK.md) — host and guest networks, the two-bridge trap
- [ROUTER_BINDINGS.md](ROUTER_BINDINGS.md) - September 19 ARP repairs, retained rules and allocation checks
- [INVENTORY.md](INVENTORY.md) — observed guest addresses, bridges, boot policy
- [TAILSCALE_PLAN.md](TAILSCALE_PLAN.md) — MagicDNS and the tailnet
- [DOMAINS.md](DOMAINS.md) — domains Stephen owns
- yesod notes `ys-yes-81xu` (the blocker this closed), `ys-yes-ljwz` (gateway
  resolver blips), `ys-yes-19c3` (NTP pinned as a literal), `ys-yes-z43q`
  (leases are not sticky by MAC)
