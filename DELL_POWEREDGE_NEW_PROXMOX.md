# New Proxmox Host — Dell PowerEdge R740xd (Reykhl)

## Overview

Replacement for the current Proxmox node `seykhl` (192.168.0.202). Ordered from
[NewServerLife](https://newserverlife.com/estimate/cc857b5fed46980ee3cd62f82c76be69/1fc3c807295b07e084dc001f256e843d/2fa331d7a1d1ec1871bb7c6bf2a05370/change-12344523/).

- **Document Version:** 2026-07-25
- **Sales call scheduled:** 2026-07-29 (Wednesday)
- **Expected arrival:** ~5–10 business days after order placement
- **Codename:** `reykhl` (placeholder; pick a final hostname before bringing it up)

---

## Confirmed Final Spec (target ~$1,791)

| Component | Selection | Price |
|-----------|-----------|-------|
| Chassis | Dell PowerEdge R740xd 24SFF (Gen14, 2U) | included |
| CPU | **2× Intel Xeon Gold 6242R** — 20c/40t ×2 = 40c/80t, 3.10 GHz base / 4.00 GHz boost, 150W TDP | **$438** (SALE 69% off $1,398) |
| RAM | 4× 32GB DDR4 PC4-19200 2400MHz RDIMM = 128 GB (1 DIMM per channel × 4 channels populated; 8 DIMM slots free) | included |
| Boot storage (front bay, RAID-1) | 2× SSD 480GB SATA 2.5" 6Gb/s with caddies | included |
| Empty caddies | 6× Dell SAS/SATA Tray Caddy 2.5" for Gen14 (for staggered drive fills) | included |
| RAID | Dell PERC H730p 2GB PCIe — will be flipped to **HBA / non-RAID mode** in iDRAC for ZFS | included |
| NIC | Dell Broadcom 57800-T 2× 10Gb BASE-T + 2× 1Gb BASE-T (0G8RPD) | included |
| Remote mgmt | iDRAC9 Enterprise | included |
| BOSS card | **Not added** — boot lives on front-bay 480GB SSDs | $0 |
| TPM | **Not added** — Windows Server 2022/2025 supported without TPM; not needed for Linux fleet | $0 |
| PSU | 2× DELL 750W for Gen Rx13/14 (hot-plug, redundant) | included |
| GPU | None — dedicated GPU host planned separately | $0 |
| Colocation | None — self-hosted on-prem | $0 |
| Warranty | Standard 1-year including HDD/SSD | included |
| Shipping | Free shipping to US (lower 48 + Canada) | $0 |

**Total: ~$1,791**

---

## Why we picked what we picked

### CPU: Gold 6242R over the on-menu Gold 6230

The original config had 2× Gold 6230 ($100) — 40c/80t at 2.10 GHz base.

The seller also had a hidden-gem 2× **Gold 6242R** at **$438** (sitting on a 69%-off SALE
from $1,398). That SKU is:

- Same 20c/40t per CPU as 6230 — same core density, same 12 memory channels
  total, same 96 PCIe 3.0 lanes total
- **3.10 GHz base clock vs 2.10 GHz** = ~45–50% more single-threaded throughput
- Cascade Lake refresh — full Spectre/Meltdown microcode, same platform as 6230
- 150W TDP per CPU (+25W each vs. 6230) → ~480–600W real wall draw

Conclusion for an AI-agent / Yesod / Dolt / Postgres workload where single-thread
loops dominate per-agent cycles: the **+$338 price delta is the single best
spend** in the entire config. Better than another SSD, better than another
64 GB of RAM.

> Action: confirm in writing on the sales call that the SKU is
> **"2× Intel Xeon Gold 6242R"** — not "6242" (no R — different chip), not
> "6230" (different base clock).

### RAM: shipped 128 GB; not pre-bought

The 4× 32GB = 128 GB config leaves 8 DIMM slots free, 4 channels per CPU empty.
Plenty of headroom today (seykhl had 30 GB total and was overcommitted 3.1×).
Will revisit only if VM density or ZFS ARC size demands it. Used 32GB
DDR4-2933 RDIMMs run ~$15–25 each; → 192 GB is +$60–100, 384 GB is +$120–200 if needed.

### BOSS card: NOT added, on purpose

For +$460 the Dell BOSS-S1 (SATA M.2 ×2) gives OS/storage isolation and frees
2 front bays. Given 24 bays and a budget that should go toward more VM storage
instead, BOSS is the wrong spend here. The 2× 480GB SSDs in RAID-1 (or ZFS
mirror) hold Proxmox boot cleanly.

### TPM: NOT added, on purpose

TPM 2.0 is only required for **Windows 11**. Linux fleet runs without it;
Windows Server 2022/2025 does not require it. Save the $30.

### PSU: 2× 750W, NOT bumped to 1100W

Real-world peak draw with this build + 24 SSDs populated: ~550–600W.
750W PSUs at 75–80% load sit in the Platinum-efficiency sweet spot. Either
PSU alone can carry the full load → redundancy is real, not nominal. The
bump to 1100W is only justified if a discrete GPU is added later — and
AI/GPU workloads will live on a separate specialized host anyway.

### H730p: HBA / non-RAID mode before Proxmox install

The PERC H730p defaults to hardware RAID mode. To use ZFS or software-managed
storage properly, set the controller to **non-RAID / HBA mode** in the iDRAC PERC
configuration utility before installing Proxmox. Otherwise ZFS will fight it
on every disk operation. (If a single VM volume leg needs hardware-RAID
mirroring later, H730p can still do that — but globally, leave it in HBA.)

---

## Drive expansion plan — staggered over the first year

The chassis ships with 22 empty front bays. Fill them gradually as budget
allows and deals surface. **Enterprise-grade SSDs only** (PM883, PM893, Micron
5300/5400, Intel S4500/S4610, Kingston DC500M). Avoid consumer brands
(870 EVO, MX500, WD Blue) and QLC drives (870 QVO, 660p, Crucial P1).

| Phase | When | What | Approx cost |
|-------|------|------|-------------|
| 1 | Ship day | 2× 480GB SSDs (boot, RAID-1 mirror) — already included | $0 |
| 2 | Month 1–2 | 8–12× enterprise 256GB SSDs in lots of 10+ (~$10–15 ea) | $80–180 |
| 3 | Month 3–6 | 2–4× used 960GB–2TB enterprise SATA SSDs | $80–320 |
| 4 | As needed | Top up remaining bays with whatever good deals appear | variable |

Sketch the ZFS layout before Phase 2 — keep vdevs to ≤8 drives; prefer mirror
vdevs over RAID-Z for VM storage; isolate the database pool (Dolt, Postgres)
onto its own mirror vdev for predictable latency.

---

## Migration plan: seykhl → reykhl

### Pre-cutover checklist

- [ ] Receive and rack reykhl in target location (basement, closet, garage — somewhere with airflow; NOT desk-side)
- [ ] Install rails + cable management arm if not already
- [ ] Connect iDRAC dedicated port to management VLAN or LAN
- [ ] Apply current BIOS + iDRAC firmware bundle (verify "≥2024 cascade Lake-R microcode present")
- [ ] Set PERC H730p to HBA / non-RAID mode
- [ ] Decide nickname (reykhl is the placeholder) and reserve IP on DHCP
- [ ] Install Proxmox VE on the 2× 480GB SSDs (ZFS mirror on H730p)
- [ ] Update SSH `~/.ssh/config` and `/etc/hosts` on admin machines ONCE new IP is assigned

### VM migration (rolling, in this order)

1. **doltsvr (VMID 100)** — Dolt server, 24GB / 64GB / Tailscale — back up `~/doltdb/databases/` to NAS first; use `qm copy` if storage bridge is set up, otherwise `qm export + qm import`
2. **yesod-postgres-server (VMID 102)** — 6GB / 60GB / Tailscale — `pg_dumpall` then restore
3. **yesod-runners (VMIDs 106, 108, 110)** — 16GB each — these were cloned from VMID 109 template; bring up empty on new box from the running template clone instead of cloning across the bridge
4. **dertog (VMID 104)** — 6GB / 30GB dashboard server
5. **seykhl-actions-runner (VMID 103)** — 4GB / 30GB — GitHub Actions runner host; re-register all repository-scoped runners on GitHub
6. **aicoe-social-runner (VMID 105)** — 2GB / 20GB
7. **n8n-server (VMID 107)** — 4GB / 30GB — re-import workflows from the n8n UI or backup
8. **sb-edge (VMID 111)** — 4GB / 20GB Supabase Edge — reconfigure Deno + edge-runtime
9. **yesod-dispatch (VMID 112)** — 4GB / 20GB / Tailscale
10. **docuseal (VMID 113)** — 2GB / 20GB / Tailscale
11. **drawio (VMID 114)** — 2GB / 20GB diagram server
12. **dynamodb-local (CTID 115, LXC)** — 1 core / 1GB / 8GB — trivial to recreate from scratch on the new node (see DYNAMODB_LOCAL.md); otherwise migrate with `pct migrate` or backup/restore

Then optional / on-demand:
- jeffrey-dev (VMID 101) — recreate fresh from base image
- test-full-201 (VMID 203) and opensymphony-base (VMID 205) — recreate if needed

### Tailscale nodes that need re-keying on the new box

- `doltsvr` (100.101.145.38)
- `yesod-postgres-server` (100.115.10.68)
- `yesod-dispatch` (100.123.34.77)
- `docuseal` (100.117.77.67)
- `sb-edge` (100.115.156.68)

Use `tailscale login` on the new host after VM migration, then re-key
upstream machine definitions.

### Make sure these DSNs are pinned to LAN IPs (not hostname)

Per YESOD-RUNNER.md line 384 — libpq resolves hostnames via
systemd-resolved and may pick IPv6 fe80/fd60 addresses that break
post-reboot. **Always use `postgresql://stephen:****@192.168.0.<ip>:5432/...`**,
never the hostname form. Pin in `runner.yaml` AND in `/etc/yesod/runner.env`
(`YESOD_POSTGRES_DSN`) AND in the LaunchAgent plist for Mac runners.

### Post-cutover

- [ ] Update `README.md` to point Infrastructure Overview at the new hostname/IP
- [ ] Update `web/seykhl-health/seykhl-health.py` → rename to `reykhl-health.py`, point at new node
- [ ] Update `web/cluster-services/index.html` cluster reference text
- [ ] Update `YESOD-RUNNER.md`, `YESOD_POSTGRES_SERVER.md`, etc. with new host
- [ ] Decommission seykhl (wipe disks, sell/trash)
- [ ] Update DNS reservations to free 192.168.0.202

---

## To-do

- [x] Confirm final component selection (RAM, BOSS, TPM, PSU, GPU all decided)
- [x] Decide on CPU upgrade: 2× Gold 6242R over 6230
- [x] Skip BOSS, TPM, GPU upgrades
- [x] Skip PSU bump to 1100W
- [ ] Sales call **2026-07-29**:
  - [ ] Confirm "2× Intel Xeon Gold **6242R**" SKU in writing (no typos)
  - [ ] Confirm RAM speed (2933 if available at no extra cost — get it)
  - [ ] Confirm PERC H730p firmware supports HBA / non-RAID mode
  - [ ] Confirm rails + bezels are in the box (Gen14 specific kit)
  - [ ] Confirm iDRAC default password is delivered in email
  - [ ] Confirm BIOS/iDRAC firmware is recent (≥2024 bundle)
  - [ ] Get freight class + weight quote (full load ≈ 50–60 lb)
- [ ] Place order after sales call
- [ ] Plan rack location with airflow + noise tolerance
- [ ] Sketch ZFS layout for 24-bay chassis before first drive fill
- [ ] Backup seykhl before any migration begins
- [ ] Migrate VMs in order (see Migration plan above)
- [ ] Update admin SSH config + /etc/hosts entries in lockstep
- [ ] Re-key Tailscale on the 5 VMs that have it
- [ ] Decommission old seykhl
- [ ] Update infrastructure documentation (README, individual VM docs)
- [ ] Buy enterprise-pullout 256GB SSDs in lots of 10+ over first 6 months

---

## Notes

- All dollar amounts above are mid-2026 ballparks from seller catalog; only the
  quoted total from the sales call is binding.
- Free shipping is to US (lower 48) and Canada. AK / HI / PR require quote.
- Configuration turnaround time on the seller's side: ≤3 business days.
- The dealer is `newserverlife.com`, a Miami-based refurb reseller; standard
  1-yr warranty includes HDD/SSD. Consider negotiating up to 2-yr coverage if
  spend exceeds $7.5k (won't apply here, but useful to know if contract grows).
