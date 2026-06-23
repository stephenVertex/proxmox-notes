# Version Inventory & Upgrade Notes

This document tracks the versions of core infrastructure software across the self-hosted cluster and notes where upgrades are available.

## Quick Summary

| Software | Latest | Cluster State | Action Needed |
|----------|--------|---------------|---------------|
| **Dolt** | 2.1.9 | 2.1.0 on `doltsvr`; not installed on runners/dertog | Upgrade `doltsvr` |
| **PostgreSQL** | 18.4 | 17.10 on `yesod-postgres-server` and `yesod-runner-3` | Major upgrade possible |
| **Beads (`bd`)** | 1.0.4 | 1.0.4 on local Mac and yesod runners; not installed on servers | None |

---

## Dolt

Dolt is the version-controlled SQL database used by Beads workspaces. Server mode is enabled on `doltsvr` (192.168.0.150).

| Host | Version | Location | Notes |
|------|---------|----------|-------|
| **doltsvr** | 2.1.0 | `/usr/local/bin/dolt` | Dolt SQL server runs here. Warning reports 2.1.9 available. |
| **Local Mac** | 2.0.1 | `/opt/homebrew/bin/dolt` | Warning reports 2.1.8 (stale check). |
| **dertog** | not installed | — | Health checks now use `pymysql` instead of the `dolt` CLI. |
| **yesod-postgres-server** | not installed | — | Not needed on this host. |
| **yesod-runner** | not installed | — | Not needed on this host. |
| **yesod-runner-2** | not installed | — | Not needed on this host. |
| **yesod-runner-3** | not installed | — | Not needed on this host. |
| **homestar-runner** | not installed | — | GitHub Actions runner; not needed. |

**Latest release:** [2.1.9](https://github.com/dolthub/dolt) (confirmed 2026-06-23).

**Recommended next step:** upgrade `doltsvr` to 2.1.9. The Dolt SQL server must be restarted during the upgrade, so plan for a brief Beads/yesod downtime window.

---

## PostgreSQL

PostgreSQL hosts the yesod catalog (`yesod-postgres-server`, 192.168.0.155).

| Host | Version | Location / Package | Notes |
|------|---------|---------------------|-------|
| **yesod-postgres-server** | 17.10 | `postgresql-17` (Debian 17.10-0+deb13u1) | Primary catalog server. |
| **yesod-runner-3** | 17.10 client | `postgresql-client-17` | Has `psql` client installed. |
| **yesod-runner** | not installed | — | No client or server installed. |
| **yesod-runner-2** | not installed | — | No client or server installed. |
| **dertog** | not installed | — | No PostgreSQL client installed. |
| **doltsvr** | not installed | — | No PostgreSQL client installed. |
| **homestar-runner** | not installed | — | No PostgreSQL client installed. |
| **Local Mac** | not installed | — | No PostgreSQL client installed. |

**Latest stable release:** [18.4](https://www.postgresql.org/) (released 2026-05-14). PostgreSQL 19 is in beta.

**Recommended next step:** PostgreSQL 17 is still supported. A move to 18.4 is a major-version upgrade requiring `pg_dump`/`pg_upgrade` or logical replication. Plan this during a maintenance window.

---

## Beads (`bd` CLI)

Beads is the distributed graph issue tracker used by yesod and agent runners.

| Host | Version | Location / Install | Notes |
|------|---------|---------------------|-------|
| **Local Mac** | 1.0.4 | `/opt/homebrew/bin/bd` (Homebrew) | Development machine. |
| **yesod-runner** | 1.0.4 | `bd` binary | Uses server-mode Dolt on `doltsvr`. |
| **yesod-runner-2** | 1.0.4 | `bd` binary | Uses server-mode Dolt on `doltsvr`. |
| **yesod-runner-3** | 1.0.4 | `bd` binary | Uses server-mode Dolt on `doltsvr`. |
| **dertog** | not installed | — | Not needed here. |
| **doltsvr** | not installed | — | Not needed here. |
| **yesod-postgres-server** | not installed | — | Not needed here. |
| **homestar-runner** | not installed | — | GitHub Actions runner; not needed. |

**Latest release:** [1.0.4](https://github.com/gastownhall/beads) (released 2026-05-09).

**Recommended next step:** none. All hosts that need `bd` are current.

---

## yesod / yesod-api

The `yesod` CLI and web UI are installed from the `yesod-refinery` source tree (which currently tracks the `yesod-aicoe` repository).

| Host | Install Location | Notes |
|------|-----------------|-------|
| **Local Mac** | `~/.local/share/uv/tools/yesod` (uv tool) | Used for development and local `yesod health`. |
| **dertog** | `/home/stephen/yesod-api/.venv` | Runs `yesod serve` on port 8090 and `yesod live_viz_ws` on port 8765. Source is a manual copy of the yesod package. |
| **yesod runners** | — | Runners invoke `yesod` commands inside worktrees; they do not run a persistent service. |

**Recommended next step:** automate deployment of the yesod source to `dertog:/home/stephen/yesod-api` so the installed copy does not drift from the source repository.

---

## Other Services

| Service | Host | Port | Status |
|---------|------|------|--------|
| yesod HTTP API + site | dertog | 8090 | Running |
| yesod live-viz WebSocket | dertog | 8765 | Running |
| cluster-services index | dertog | 8092 | Running |
| Seykhl health dashboard | dertog | 8093 | Running |
| db-details dashboard | dertog | 8094 | Running |
| clip-together frontend | dertog | 8091 | Running |
| SJBIS | dertog | 7878 | Running |
| Tailscale HTTPS | dertog | 443 | Running |
| Dolt SQL server | doltsvr | 3306 | Running |
| PostgreSQL | yesod-postgres-server | 5432 | Running |
| GitHub Actions runner | homestar-runner | — | Running, label `dertog-deploy` |

---

## Upgrade Priority

1. **Dolt on `doltsvr`** — low-risk patch release (2.1.0 → 2.1.9). Plan a short restart window.
2. **PostgreSQL on `yesod-postgres-server`** — major upgrade (17 → 18). Requires backup + migration plan. Not urgent; 17 is still supported.
3. **yesod deployment automation** — process improvement, not a version upgrade. Prevents drift between source and dertog copy.
4. **Beads / `bd`** — no action. Current on all hosts that use it.
