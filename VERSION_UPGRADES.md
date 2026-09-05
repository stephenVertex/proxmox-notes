# Installed software versions

**Verified:** 2026-09-05 from installed packages, running containers and version
commands. This page records deployed versions; it makes no claim about the
latest upstream release and does not authorize upgrades.

| Component | Host / guest | Observed version |
|---|---|---|
| Proxmox | Sefer | 9.2.2; kernel `7.0.2-6-pve` |
| Proxmox | Seykhl | 9.1.1; kernel `6.17.2-1-pve` |
| Dolt write primary | Sefer VM 124 | 2.1.10 |
| Dolt static seed | Sefer VM 100 | 2.3.1; SQL disabled |
| Dolt binary | Sefer VM 130 Ibur | 2.1.10 |
| PostgreSQL | Sefer VMs 102, 110 and 121 | 17.11 package; running native clusters |
| pgvector | Sefer VMs 102 and 130 | 0.8.0-1 package installed |
| Test PostgreSQL | Sefer's 19 running LXC guests | PostgreSQL 16 `main` online |
| LiteLLM | Sefer VM 101 | `ghcr.io/berriai/litellm:v1.98.0` |
| LiteLLM database | Sefer VM 101 | `postgres:17-alpine` container |
| LiteLLM proxy | Sefer VM 101 | `caddy:2.10-alpine` container |
| GitLab EE | Sefer VM 119 | 19.3.1-ee.0 |
| GitLab Runner | Sefer VM 120 | 19.3.1-1 |
| Docker Engine | GitLab Runner, DocuSeal, draw.io, Bukher | 29.7.2 package |
| n8n | Sefer VM 107 | 2.8.4 |
| Neo4j | Sefer VM 118 | `neo4j:2026.07.1` |
| SigNoz | Sefer VM 117 | `signoz/signoz:v0.137.0` |
| SigNoz collector | Sefer VM 117 | `signoz/signoz-otel-collector:v0.144.8` |
| SigNoz ClickHouse / Keeper | Sefer VM 117 | 25.12.5 images |
| SigNoz metadata database | Sefer VM 117 | `postgres:16` container |
| Semantic graph release | Sefer VM 121 | `dac21c562713` symlink target |
| Local Beads CLI | Administrator Mac | 1.1.0 (Homebrew) |

`docuseal/docuseal:latest`, `jgraph/drawio`, `diygod/rsshub:latest`,
`miniflux/miniflux:latest` and `supabase/realtime:latest` are the configured
image references. A mutable tag is not an exact application version; the
audit did not infer release numbers from those tags.

## Operating systems and inactive installations

The inspected service guests run Debian 13 except n8n, which runs Debian 12.
The historical Dolt page's Ubuntu label was corrected from the guest's live
`/etc/os-release`. Jeffrey-dev and other stopped guests were not booted to
verify their installed OS or tools.

The newer runner/gate VMs commonly contain a PostgreSQL 17 cluster in the
down state. Their online test database is a separate PostgreSQL 16 container;
an installed package must not be equated with an active service.

## Deployment and upgrade boundaries

Dertog's active Yesod service still uses `/home/stephen/yesod-api`, while
newer runners/controllers have `/srv/yesod` and `/opt/yesod`. The fleet is not
one uniform copy of the old June installation. See [YESOD-RUNNER.md](YESOD-RUNNER.md)
and [DERTOG.md](DERTOG.md) for observed services.

Historical claims that Dolt was 2.1.0, only three GitHub runners existed, or
all runners were active are superseded by this inventory. The older
upstream-version recommendations were removed rather than silently reused.
Before any upgrade, inspect the actual service version, its matching release
notes, current backup/restore evidence and active workload. No upgrades were
performed during this documentation refresh.
