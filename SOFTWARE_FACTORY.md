# Software Factory — Cluster Architecture & Workload Plan

**Planning record, reviewed 2026-09-05.** The current deployment is two
active standalone Proxmox hosts: Sefer and Seykhl. Seykhl was repurposed for
g2 gates rather than decommissioned. The proposed multi-R740xd/DGX architecture
below is not a claim about installed capacity. See [README.md](README.md)
and [YESOD-RUNNER.md](YESOD-RUNNER.md) for the live fleet.

## Overview

- **Document Version:** 2026-07-25
- **Author:** stephen
- **Scope:** Long-term plan for the "couple more boxes" expansion beyond the initial seykhl replacement. Captures the multi-cluster architecture (DGX Sparks + R740xds) and where each workload type lives.

**Read alongside:**

- [DELL_POWEREDGE_NEW_PROXMOX.md](DELL_POWEREDGE_NEW_PROXMOX.md) — the immediate purchase + first migration steps for the primary Proxmox host.

**When this plan starts applying:**

- The single new R740xd has shipped and seykhl is decommissioned
- A 4-node DGX Spark cluster is wired up
- 1–4 additional R740xds are added over time to expand capacity

---

## Top-line architecture

**Compute is hybrid: 4 DGX Sparks (inference / agent reasoning) + N R740xds (execution / state / storage).**

```
┌────────────────────── Inference / Reasoning ──────────────────────┐
│             4× NVIDIA DGX Spark (Grace Blackwell GB10)            │
│       Local LLM serving + agent reasoning + planning loops       │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ 1Gb / 10Gb LAN + Tailscale
                                 ▼
┌──────────── Execution / Storage / Orchestration ────────────────┐
│                  N× Dell PowerEdge R740xd (Gen14)                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Node 1: Conductor (orchestration, queue, identity, db)     │ │
│  │ Node 2: Sandbox Farm (ephemeral execution environments)    │ │
│  │ Node 3: Builder (compile / test farm)                      │ │
│  │ Node 4: Vault / Video Vault (state, archive, LanceDB)      │ │
│  │ Node 5: Bridge (public services, Tailscale ingress)        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**Roles don't cross.** DGX Sparks do model work (inference, tool-calling, planning). R740xds do execution, state, I/O, network edge. State lives only on R740xds. Sparks are reusable in seconds; databases are not.

---

## Why this split

- **Sparks are wrong for state**, **R740xds are wrong for inference** — they have different strengths and should not duplicate the other's weakness.
- **Sparks are also wrong for orchestration.** Orchestrator uptime has to outlast model reloading; keep it on boring hardware with iDRAC + UPS.
- **R740xd is well-suited to graph workloads and surveillance storage** because of ECC RAM, 12 memory channels, 24 drive bays, mature single-thread CPUs.
- **5 R740xds = enough for HA quorum on the parts that matter** (etcd, Postgres replication, Ceph). Without a 3-node floor, you can build 5-node HA trivially.

---

## Concrete 5-node roles (current plan)

| Node | Role | Workload shape | Critical? |
|------|------|----------------|-----------|
| **1 — Conductor** | Yesod dispatcher, queue, identity, secrets, Postgres + pgvector, audit logs, all integration daemons (IMAP, calendar, social) | Low/moderate CPU, persistent network egress, uptime-critical | **YES** — orchestrator dies = factory dies |
| **2 — Sandbox Farm** | Ephemeral execution: Firecracker, Docker, Nix shells, Playwright, temp Linux VMs per agent task, ephemeral sweeper forks | High churn, fast SSDs, most I/O pressure | NO — task should be retryable |
| **3 — Builder** | sccache, distcc, Bazel remote cache, Rust/C++/Go compile farm, lint, test execution, source trees | CPU/RAM heavy in bursts; idle in lulls; NVMe critical | NO — recoverable from source |
| **4 — Vault** | MinIO / SeaweedFS, code archive, surveillance video archive + LanceDB index, restic-to-B2 staging, Postgres replica for DR | Slow-pulse, fat storage (SSD hot + spinning cold), graph DB mirror | HIGH — loss of this is loss of memory |
| **5 — Bridge** | Public services (sb-edge, docuseal, GitHub Actions runner), reverse proxy, Tailscale ingress, webhook receptions, lightweight web UIs for review | Network-edge first, isolated blast radius | MEDIUM — sacrificial if compromised |

**Specialization principle:** one node is the "explode safely" box where experiments go. The other four stay stable. Solo operators with too many boxes tend to over-isolate; designate one explicitly.

---

## Workload distribution

### Storage / state layer

| Substrate | Where | Why |
|-----------|-------|-----|
| Postgres (operational) | Node 1 (primary) + Node 4 (replica) | Operational data needs durability + DR |
| pgvector (semantic recall over Postgres data) | Node 1 | Small enough to live with primary |
| LanceDB (multi-modal: surveillance, code, audio, email) | Node 4 (Vault) | Tiered: SSD hot + spinning cold archive |
| Neo4j (graph: code, knowledge, decisions) | Node 1 OR dedicated 6th node | ECC + 12 mem channels + 24 bays are tailor-made |
| MinIO / SeaweedFS (object blob) | Node 4 (Vault) | Cheap bulk spinning + SSD hot tier |
| ZFS send/receive + restic to Backblaze B2 | Node 4 → offsite | Cheap 99% durability on everything |

### Compute layer

| Workload | Where | Why |
|----------|-------|-----|
| Inference (LLM, VLM, embeddings) | DGX Sparks | GPUs; can't be done well on R740xd |
| Agent dispatch / planning | DGX Sparks + Node 1 (state) | Inference on Sparks, state on Conductor |
| Compilation / testing (Rust, C++, Go) | Node 3 (Builder) | Heavy CPU + sccache pool |
| Ephemeral execution sandboxes | Node 2 (Sandbox Farm) | High I/O churn, isolated blast radius |
| Web hosting / webhooks / GitHub Actions runner | Node 5 (Bridge) | Public exposure isolated |
| Surveillance YOLO + motion | Coral TPU on NAS | Canonical good setup; DON'T disturb |
| Surveillance embedding + captioning (LanceDB ingest) | DGX Sparks (CLIP/SigLIP/VLM) | GPU-bound; batches nicely overnight |

### Integration layer

| Workload | Where |
|----------|-------|
| Sweep daemons (social: Twitter/X, Reddit, HN, LinkedIn, Mastodon) | Node 1 — small VMs, one per source |
| IMAP watcher + email ingestion | Node 1 — IDLE daemon + Postgres |
| Calendar / CalDAV / personal planning | Node 1 — small VM with Postgres + web UI on Node 5 |
| Calendar invite detection, action-item extraction (inference) | DGX Sparks |
| Web UI for review ("today's emails," "social mentions") | Node 5 — Tailscale-gated |
| Long-term archive of integrated streams | Node 4 (Vault) with TTL |

---

## Specific workload deep dives

### 1. Graph databases (Neo4j primary)

**Why R740xd:** ECC RAM + 12 memory channels + 24 front bays + mature single-thread = custom-tailored for graph workloads.

**Stack:**
- Neo4j Community Edition as primary
- Memgraph as fallback / streaming-graph alternative
- Bolt protocol everywhere (LLM-writable, easy agent integration)

**Use cases in this factory:**
- **Code-as-graph** — modules, classes, functions, calls, imports. Powers semantic search, "find all callers," impact analysis.
- **Knowledge graph over the domain** — entities + relations as long-term agent memory, more structured than pure vector RAG.
- **Decision / workflow graph** — agent dispatch DAG, audit trail, replayable workflows.
- **Build / dep graph** — externalized Cargo/eslint dependency graph, queryable by agents.

**Sizing math:**
- 16–32 GB Neo4j heap + 64–128 GB page cache on a single node handles 5–15 million nodes interactively.
- Save the rest of the 128–384 GB RAM for agent-side workloads in the same box.

**Placement options:**
- Option A — Bolt onto Conductor (Node 1): low-latency for the orchestrator; consolidating
- Option B — Dedicated 6th node (or share with Vault Node 4): isolated memory pressure, more sizing flexibility

**Recommendation:** Option B if the graph workload is steady; Option A if it's bursty and small. Default to Option B — fire-prone workloads want their own RAM budget.

**Avoid:**
- Don't run graph queries on Sparks (graph traversal parallelizes awkwardly; RAM/CPU-bound is what works).
- Don't isolate Neo4j to one CPU socket — balance across both NUMA nodes.
- Don't back up via file snapshots — use `neo4j-admin backup` and write to Node 4.

### 2. LanceDB + surveillance video indexing

**Existing setup (DO NOT change):**
- Cameras + Frigate + Google Coral TPU on NAS
- All real-time motion + YOLO detection runs on Coral
- This is canonical and battle-tested. Leave it alone.

**What LanceDB adds (semantic recall Coral can't):**
- Natural-language search ("show me when the delivery happened yesterday")
- Similarity lookup ("find clips like this one")
- Auto-captioning (VLM per clip)
- Cross-camera event clustering

**Pipeline:**
```
Cameras → Frigate + Coral (NAS, unchanged)
            │
            │ MQTT events + snapshot frames
            ▼
   Event-ingest daemon on Node 4 (Vault)
            │
            │ batched overnight
            ▼
   DGX Spark: CLIP / SigLIP embedding + VLM caption
            │
            ▼
   LanceDB table on Node 4 (single row per event segment)
            │
            ▼
   Tailscale web UI on Node 5: "search my house"
```

**Sizing (4-camera 1080p with motion-only recording):**
- Raw video: 30–80 GB/day → 10–30 TB/year
- LanceDB rows: ~10k–30k per day, ~50 MB/day of vectors, ~50 GB/year
- Spark inference: ~30 min of one Spark per day for all embeddings
- Storage tier: 2× 2 TB SSD mirror for hot + LanceDB; 8–12× spinning bulk in RAID-Z2 for archive

**Privacy posture (NON-NEGOTIABLE):**
- On-prem only. No cloud routes for raw or embeddings.
- ZFS native encryption on Vault vdev. LUKS if preferred.
- Camera creds in a vault backend (Vaultwarden on Node 1 fine). Never plain `.env`.
- Face recognition OFF by default until explicitly enabled with consent.
- Retention policy written down BEFORE ingest. Suggested: raw 90 days, embeddings/captions forever.

**Alternatives if LanceDB doesn't fit:**
- Marqo — better out-of-the-box UI, heavier at scale
- Twelve Labs — hosted mostly, excellent for video quality
- VideoDB — purpose-built for video search
- Frigate + local LLaVA captions only — minimum viable if natural-language queries aren't needed

### 3. Social media sweeps

**Pattern:** one small VM per source. Cloned from `aicoe-social-runner` (current VMID 105). Each VM:
- Periodic scraper + rate-limit-aware backoff
- Tiny Postgres for state (cursor, retry queue)
- LLM classifier call-out to a Spark for actual inference

**Sweepers:** `social-twitter`, `social-reddit`, `social-hn`, `social-linkedin`, `social-mastodon`. Each on its own VM, its own secrets, its own key.

**Inferred facts / digests** stored in LanceDB (Node 4) for long-term semantic recall.

### 4. Email analysis

**Pipeline:**
- IMAP IDLE watcher daemon on Node 1 (Conductor) tail-ingests
- Postgres row per message: from, subject, snippet, labels
- LLM-generated embedding + summary + extracted entities → via Spark
- LanceDB for semantic search ("show me contracts mentioning X")
- Calendar invites / invoices / action items detected and surfaced

**Node 5 (Bridge)** hosts a Tailscale-only web UI ("today's email digest") → mirrors the existing `dertog` dashboard pattern.

### 5. Personal / project planning

- **Agent dispatch planning (Yesod/Spark):** lives on Node 1 + the Spark cluster. Already covered.
- **Personal calendar / life planning:** small Node 1 VM, CalDAV, Tailscale UI on Node 5.
- **Project planning (sprints, roadmaps):** same — Node 1 VM with Postgres + web UI on Node 5.

**Cheap and effective.** Don't specialize here beyond what's already known.

---

## Cross-cluster wiring

### Network

| Path | Speed | Purpose |
|------|-------|---------|
| Sparks ↔ Node 1 (Conductor) | 1 Gb (control) + 10 Gb (data) | Dispatch + result delivery |
| R740xds ↔ R740xds | 10 Gb to a managed switch | Cross-node ZFS replication, Postgres replication, LanceDB queries |
| Nodes ↔ NAS (Frigate archive + restic staging) | 1–10 Gb | Surveillance archive + backups |
| iDRAC dedicated NIC | 1 Gb to management VLAN | Out-of-band rescue; never goes through OS |
| Everything to/from internet | 1 Gb upstream | Single managed egress via Node 5 |
| Sparks ↔ R740xds ↔ User | Tailscale (over WireGuard) | Tailscale-only web UIs, observability |

### Identity / secrets

- Single Vaultwarden on Node 1 OR 1Password CLI
- Per-integration API key isolated per VM
- Audit key rotation every 90 days
- Camera creds, OAuth tokens, API keys — never in plain `.env`

### Queue / message bus

- Likely Redis or NATS on Node 1 for inter-agent messages
- Optional: Postgres LISTEN/NOTIFY if queue requirements are simple
- Skip Kafka / RabbitMQ — overkill for this scale

---

## Build / migration sequence

### Phase 0 — Land the first R740xd, replace seykhl
See [DELL_POWEREDGE_NEW_PROXMOX.md](DELL_POWEREDGE_NEW_PROXMOX.md) for the spec, ordering checklist, migration runbook.

### Phase 1 — Stand up the dedicated roles
After seykhl is decommissioned and the new box is running your fleet:
- Re-arrange VMs by role, not by VMID: conductor VMs on Conductor (Node 1), sandbox tasks on Sandbox (Node 2), etc.
- This may not require additional hardware yet — just VM placement discipline.

### Phase 2 — Bring the DGX Sparks online
- Wire 4× DGX Spark to the same 10 Gb switch
- Decide on inference serving: vLLM or llama.cpp?
- Build the dispatch path: agent on a Spark needs Node 1 queue + Node 2 sandbox + Node 4 storage. Bolt/set up Tailscale between them.

### Phase 3 — Add the 2nd and 3rd R740xd (sandbox + builder)
The first new R740xd almost certainly becomes Conductor + Bridge or Conductor + Vault. Once filled, add:
- 2nd box as **Sandbox Farm (Node 2)** — hosts per-task VMs.
- 3rd box as **Builder (Node 3)** — pounce on Rust/C++ compile cycles.

You now have a proper 3-node compute tier that matches Persona 2 (Agent Mesh).

### Phase 4 — Surveillance / LanceDB on Vault
- Migrate Frigate's archive shelf from NAS to a dedicated R740xd slot on Node 4.
- Stand up LanceDB + embed ingest pipeline using the existing Frigate MQTT events.
- Build the Tailscale web UI on Node 5.

### Phase 5 — Social / email sweeps at scale
- Fork `aicoe-social-runner` template 3–5 times for additional sources.
- Stand up the IMAP watcher.
- Connect everything to a LanceDB fact stream on Node 4.

### Phase 6 — Graph DB + graph-as-memory for agents
- Stand up Neo4j on Node 1 (or dedicated 6th node).
- Backfill: code-as-graph from your repo; entity/decision graphs from accumulated agent dispatch history.

### Phase 7 — Add 4th + 5th R740xd (HA + Ceph quorum)
- Now you have enough hardware for genuine HA: 3-node etcd quorum + 2-node capacity for variance. Add Ceph or stay on ZFS replication.

**Each phase is independent.** Don't try to do Phase 4 before Phase 1; you can skip Phase 6 for a year if the agent memory substrate isn't yet ready.

---

## Operating principles

- **State lives on R740xds, never on Sparks.** Modeling state on a GPU box is a recipe for chaos.
- **Orchestrator lives on iDRAC + UPS hardware.** No compromises.
- **One designated "explode safely" node.** Otherwise solo operators over-isolate and end up with 5 boxes each holding 4 stable VMs (sadly not 'production-grade').
- **Retention policy written before ingest.** Surveillance, social, email — all unbounded by default. Decide and automate.
- **Encryption at rest by default for any private data.** Surveillance especially.
- **Watch the electricity bill.** 1 R740xd is fine. 5 is $150–250/month in many US regions. Solar helps; battery does too. Don't pretend it doesn't matter.
- **Name things consistently.** `node-N.role` convention; it pays off when you have 9 boxes and have to SSH from memory.

---

## Garage deployment specifics

Tunables for the R740xd fleet hosted in a residential garage:

- **Power:** dedicated 20A circuit per server; L6-20R (240V/20A twist-lock) preferred over 120V for better wire utilization on long garage runs. Existing dryer outlet (NEMA 14-30R) is a free 240V source if available.
- **Cooling:** garage ambient in summer can exceed the 35°C R740xd operating range. Either a mini-split for the rack zone or a passive exhaust fan to outside is necessary before summer 2.
- **Dust:** sealed 12U rack cabinet with active intake filter, OR scheduled compressed-air blowouts quarterly.
- **Network:** Cat6 (or two for redundancy) from main router/switch; consider fiber if the run is long.
- **UPS:** rack-mount UPS with AVR per server. Each ~$300–700 used. This is the highest-leverage reliability investment per dollar.
- **Physical security:** locked full-height rack cabinet; rack weighs > server with a determined thief.
- **Insurance:** disclose server-class gear to homeowner's policy; some require a rider.

---

## Open questions / decisions to make later

These are intentionally unresolved — they should be data-driven decisions once the box is running and you have usage data:

- **When to add the 2nd-5th R740xd** — only after first server is >70% utilized for a sustained month.
- **Whether the graph DB gets its own 6th node** — depends on whether Neo4j pressures Node 1 RAM under steady load.
- **Whether to deploy Ceph** — depends on whether ZFS send/receive + Postgres streaming replication is enough DR for you.
- **Solar / battery sizing** — depends on actual measured power draw over a billing cycle.
- **Whether to expose anything to non-Tailscale internet** — almost certainly no, but stay alert.
- **Public-facing customers** — if that ever happens, plan HA more seriously (3-node quorum floor, offsite backups, paging).

---

## To-do

- [x] Decide 5-node plan: Conductor / Sandbox / Builder / Vault / Bridge
- [x] Decide workload distribution across nodes
- [x] Decide graph DB stack: Neo4j + GDS
- [x] Decide LanceDB role for surveillance
- [x] Decide agent + integration layer pattern (one VM per source/task)
- [x] Decide hybrid Sparks + R740xd split: inference vs execution
- [ ] Order first R740xd (see [DELL_POWEREDGE_NEW_PROXMOX.md](DELL_POWEREDGE_NEW_PROXMOX.md))
- [ ] Decide VM placement convention: house all VMs on a single Conductor host first, distribute as load demands
- [ ] Stand up Conductor, Bridge, Vault roles on first R740xd in Phase 1
- [ ] Bring DGX Spark cluster online + wire dispatch
- [ ] Add 2nd/3rd R740xd in Phase 3
- [ ] Migrate Frigate archive + LanceDB to dedicated Vault in Phase 4
- [ ] Forks of `aicoe-social-runner` per source (Phase 5)
- [ ] IMAP watcher + email ingest (Phase 5)
- [ ] Neo4j + GDS stand-up (Phase 6)
- [ ] HA / Ceph quorum with 4th + 5th boxes (Phase 7, much later)

---

## Notes

- The 5-node layout described here (Conductor / Sandbox / Builder / Vault / Bridge) was refined from earlier "Persona 2 — Agent Mesh" sketch in conversation; this doc is the canonical version.
- The graph DB stack selection (Neo4j + GDS primary) is conditional on graph workloads materializing; if they don't, drop the box cost and use Node 1 Postgres + pgvector only.
- The LanceDB + surveillance section assumes the Coral TPU + Frigate pair stays configured exactly as it is today.
- This document is a forward-looking plan; revisit quarterly as actual hardware is acquired and load patterns emerge.
