# Yesod Runner Setup Documentation

**Document Version:** 2026-06-05
**Author:** OpenCode Agent

---

## Overview

The **yesod-runner** is a Debian 13 virtual machine (VMID 106) running on Proxmox node `seykhl`, designed to serve as a secondary agent dispatch runner alongside the primary `pompom` macOS runner. It enables parallel task execution and provides Linux-based execution capabilities.

### Runner Fleet

| VM ID | Name | IP | Status | Purpose |
|-------|------|-----|--------|---------|
| 106 | yesod-runner | 192.168.0.152 | Active | Primary runner |
| 108 | yesod-runner-2 | 192.168.0.148 | Active | Secondary runner |
| 109 | yesod-runner-base | N/A | Template | Template for new runners |
| 110 | yesod-runner-3 | 192.168.0.136 | Active | Tertiary runner (from template) |

---

## Access Information

### Network Details (Primary Runner)
- **IP Address:** `192.168.0.152` (was 192.168.0.146 before network reservation fix)
- **Hostname:** `yesod-runner`
- **MAC Address:** `bc:24:11:a0:58:60`
- **Proxmox Node:** `seykhl` (192.168.0.202)
- **VM ID:** 106

### SSH Access (Passwordless)

All runners are configured for passwordless SSH access using the same SSH key as your other machines:

```bash
# Primary runner
ssh stephen@yesod-runner        # alias in ~/.ssh/config
ssh stephen@192.168.0.152

# Runner 2
ssh stephen@yesod-runner-2      # alias in ~/.ssh/config
ssh stephen@192.168.0.148

# Runner 3
ssh stephen@yesod-runner-3      # alias in ~/.ssh/config
ssh stephen@192.168.0.136

# Or via Proxmox host
ssh stephen@seykhl
```

**Note:** The SSH key was installed via cloud-init during VM creation. The public key is located in `/var/lib/vz/snippets/106-cloudinit.yaml` on the Proxmox host.

### Proxmox Console Access

```bash
# Via web UI
https://192.168.0.202:8006

# Via CLI (from any host)
ssh root@192.168.0.202 "qm console 106"
```

---

## Hardware Specifications

All runners (106, 108, 110) and the template (109) use identical specs:

- **CPU:** 4 cores
- **RAM:** 8GB (7.8Gi available)
- **Disk:** 20GB
- **OS:** Debian 13 (Linux 6.12.88+deb13-amd64)
- **Architecture:** x86_64

## Template (VM 109)

The `yesod-runner-base` template contains pre-installed software for rapid deployment:

- uv 0.11.20
- cargo 1.96.0 / rustc 1.96.0
- gh CLI 2.94.0
- opencode 0.0.55
- ripgrep 14.1.1
- fzf 0.60.3
- git 2.47.3
- /etc/hosts configured for yesod infrastructure
- Generic runner.yaml (with placeholder values)

**To create a new runner from template:**
```bash
# On Proxmox host
qm clone 109 <new_id> --name yesod-runner-N --full
# Then configure: set hostname, generate SSH keys, update runner.yaml
```

---

## Software Stack

### Core System
- **OS:** Debian 13 (installed from `debian-13-generic-amd64.qcow2` cloud image)
- **Kernel:** 6.12.88+deb13-amd64
- **Package Manager:** `apt` (standard Debian)

### Development Tools
- **uv:** 0.11.19 (Python package manager, installed to `~/.local/bin`)
- **Python:** 3.14 (via uv)
- **git:** Standard Debian package
- **build-essential:** GCC, make, etc.
- **curl:** For HTTP requests

### AI Agent Binaries
- **opencode:** 0.0.55 (Linux amd64, installed from GitHub release `.deb`)
  - Location: `/usr/bin/opencode`
  - Size: ~43MB
- **ripgrep:** 14.1.1 (opencode dependency for code search)
- **fzf:** 0.60.3 (opencode dependency for fuzzy finding)
- **beads (bd):** 1.0.4 (Issue tracker / Dolt database)
  - Location: `~/.local/bin/bd` (symlinked to `/usr/local/bin/bd`)

### Yesod Application
- **Location:** `~/dev5/yesod-aicoe/yesod/`
- **Python Environment:** `.venv` (managed by uv)
- **Service:** `yesod-codefactory-dispatch.service` (systemd)
- **Database:** PostgreSQL (via `yesod-postgres-server` at 192.168.0.155:5432)

---

## Configuration Files

### 1. Runner Configuration

**File:** `~/.config/yesod/runner.yaml`

```yaml
runner_id: yesod-runner
models:
  - opencode-kimi
  - opencode-claude
  - opencode-qwen
poll_interval: 10
max_concurrent: 1
worktree_base_dir: /tmp/yesod-workdir
opencode_path: opencode
postgres_dsn: postgresql://stephen:lj*123NM@yesod-postgres-server:5432/stephen
fireworks_api_key: fw_GDwAQVjo2JwrupnfcF6LpS
model_map:
  opencode-kimi: "fireworks-custom/accounts/fireworks/routers/kimi-k2p6-turbo"
  opencode-qwen: "fireworks/accounts/fireworks/models/qwen3p6-plus"
  opencode-deepseek: "fireworks/accounts/fireworks/models/deepseek-v4-pro"
```

> **CRITICAL — model_map is mandatory for every opencode-* lane.** Without it,
> opencode resolves `opencode-kimi` / `opencode-qwen` / `opencode-deepseek` to
> opencode.ai-hosted models and hits their billing quota → "Insufficient balance",
> 0-byte agent log, instant abort with exit=None. The failure signature is
> indistinguishable from a binary-startup crash. Observed twice: runner-2
> (2026-06-10) and sjbmbp (2026-06-11). Verify by running the model directly in
> the runner env before enabling the daemon.

### 2. Environment Variables

**File:** `/etc/yesod/runner.env`

```
YESOD_POSTGRES_DSN=postgresql://stephen:lj*123NM@yesod-postgres-server:5432/stephen
FIREWORKS_API_KEY=fw_GDwAQVjo2JwrupnfcF6LpS
# Claude lane only (hosts with the claude CLI installed — see below):
ANTHROPIC_BASE_URL=https://tfy.promptlens.trilogy.com
ANTHROPIC_AUTH_TOKEN=<JWT — copy current value from the env block of ~/.claude/settings.json on sjbmbp>
```

These are loaded by the systemd service via `EnvironmentFile=/etc/yesod/runner.env`.

#### Claude lane auth — LLM gateway (since 2026-06-11)

The claude CLI authenticates through the Trilogy promptlens gateway, **not** Anthropic OAuth:

- `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` in `runner.env` (above). Source of truth for the token is the `env` block of `~/.claude/settings.json` on Stephen's Mac (sjbmbp).
- **Do NOT set `CLAUDE_CODE_OAUTH_TOKEN`** — it was removed fleet-wide on 2026-06-11 to avoid auth ambiguity. If provisioning from an old image, delete that line.
- Also check for and remove cached OAuth credentials on the host (`~/.claude/.credentials.json` and friends) — a cached cred can silently take over from the gateway.
- Only hosts running the `claude` / `claude-fable-5` lane need the claude CLI installed (as of 2026-06-11: yesod-runner and sjbmbp). The opencode-* lanes (kimi/deepseek/qwen) use OpenCode→Fireworks and need only `FIREWORKS_API_KEY`.
- **Verify after provisioning** (two-way, in a shell with runner.env sourced):
  1. `claude -p "Reply with exactly: GATEWAY-OK"` succeeds;
  2. the same command **fails** with `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN` unset — proving traffic actually goes through the gateway rather than a leftover credential.
- After env changes: `sudo systemctl restart yesod-codefactory-dispatch.service` (only when the runner has no live run — check http://dertog:8090/api/runs first).

### 3. Systemd Service

**File:** `/etc/systemd/system/yesod-codefactory-dispatch.service`

```ini
[Unit]
Description=Yesod Codefactory Dispatch Runner
After=network.target

[Service]
User=stephen
Group=stephen
Type=simple
EnvironmentFile=/etc/yesod/runner.env
Environment="PATH=/home/stephen/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/stephen/.local/bin/uv run yesod codefactory-dispatch start --foreground
WorkingDirectory=/home/stephen/dev5/yesod-aicoe/yesod
Restart=on-failure
RestartSec=10
StandardOutput=append:/tmp/yesod-codefactory-dispatch.out
StandardError=append:/tmp/yesod-codefactory-dispatch.err

[Install]
WantedBy=default.target
```

### 4. OpenCode Configuration

**File:** `~/.opencode.json`

```json
{
  "data": {
    "directory": ".opencode"
  },
  "providers": {
    "fireworks": {
      "apiKey": "{env:FIREWORKS_API_KEY}",
      "disabled": false
    }
  },
  "agents": {
    "coder": {
      "model": "fireworks/accounts/fireworks/routers/kimi-k2p6-turbo",
      "maxTokens": 5000
    },
    "task": {
      "model": "fireworks/accounts/fireworks/routers/kimi-k2p6-turbo",
      "maxTokens": 5000
    },
    "title": {
      "model": "fireworks/accounts/fireworks/routers/kimi-k2p6-turbo",
      "maxTokens": 80
    }
  },
  "shell": {
    "path": "/bin/bash",
    "args": ["-l"]
  },
  "debug": false,
  "autoCompact": true
}
```

**Alternative Config:** `~/.config/opencode/opencode.json`

Contains a more detailed provider configuration for Fireworks AI with custom models.

### 5. Beads (Issue Tracker) Configuration

**File:** `~/dev5/yesod-aicoe/.beads/config.yaml`

```yaml
backup.git-repo: "/var/tmp/yesod-aicoe-beads-autobackup"
export.auto: false
```

**Mode:** Embedded (Dolt in-process, no external server)
**Database:** `yesod_aicoe`
**Issue Prefix:** `yesod-aicoe`

### 6. Hosts File

**File:** `/etc/hosts`

Added entry:
```
192.168.0.155 yesod-postgres-server
```

### 7. Path Compatibility

For macOS path compatibility (since the repo was copied from pompom):
```bash
sudo mkdir -p /Users
sudo ln -sf /home/stephen /Users/stephen
```

---

## Setup History

### Phase 1: VM Creation
1. Created VM 106 on Proxmox node `seykhl`
2. Imported `debian-13-generic-amd64.qcow2` cloud image
3. Resized disk to 20GB
4. Configured cloud-init with SSH key and static IP (192.168.0.146)

### Phase 2: Software Installation
1. Installed `uv` 0.11.19 to `~/.local/bin`
2. Installed `git`, `build-essential`, `curl`
3. Copied `yesod-aicoe` repo from pompom via tar (git clone failed due to auth)
4. Recreated `.venv` and installed yesod with `uv pip install -e .`
5. Installed missing `click` dependency

### Phase 3: Database Connectivity
1. Added `yesod-postgres-server` to `/etc/hosts`
2. Set environment variables for PostgreSQL DSN
3. Verified connection to `yesod-postgres-server` at 192.168.0.155:5432

### Phase 4: Runner Configuration
1. Created `~/.config/yesod/runner.yaml`
2. Created `/etc/yesod/runner.env`
3. Created systemd service file
4. Set hostname to `yesod-runner`
5. Started and enabled service

### Phase 5: Agent Binaries
1. Installed `opencode` 0.0.55 from GitHub releases (`.deb` package)
2. Installed `ripgrep` and `fzf` (opencode dependencies)
3. Installed `beads (bd)` 1.0.4 via official install script
4. Symlinked `bd` to `/usr/local/bin/bd`

### Phase 6: Beads Workspace Fix
1. Fixed `.beads` ownership from `root` to `stephen:stephen`
2. Switched from server mode to embedded mode (removed `doltsvr.toml`)
3. Created backup git repo at `/var/tmp/yesod-aicoe-beads-autobackup`
4. Added `User=stephen` to systemd service to prevent root-owned files

### Phase 7: OpenCode Configuration
1. Created `~/.opencode.json` with Fireworks AI provider configuration
2. Set default model to `fireworks/accounts/fireworks/routers/kimi-k2p6-turbo`
3. Configured `{env:FIREWORKS_API_KEY}` for API key resolution

---

## Current Status

### Runner Status
All three runners are active and registered in the database:

| Runner | Status | Models | Max Concurrent |
|--------|--------|--------|----------------|
| yesod-runner | active | claude-fable-5, opencode-kimi, opencode-claude, opencode-qwen | 3 |
| yesod-runner-2 | active | claude-fable-5, opencode-kimi, opencode-claude, opencode-qwen | 3 |
| yesod-runner-3 | active | claude-fable-5, opencode-kimi, opencode-claude, opencode-qwen | 3 |

### Service Status
```bash
systemctl status yesod-codefactory-dispatch.service
```

### Verification Commands
```bash
# Check all runners
psql $YESOD_POSTGRES_DSN -c "SELECT id, status, current_tasks FROM runners;"

# Check runner status
yesod codefactory-dispatch status

# Check runner logs
yesod codefactory-dispatch logs

# Check opencode version
opencode --version

# Check bd version
bd version

# Check available models
opencode -d
```

---

## Known Limitations

1. **opencode binary must be on the LaunchAgent PATH (Mac runners):** opencode installs to `~/.opencode/bin/opencode`, which is NOT in the default LaunchAgent PATH. The dispatch daemon inherits the LaunchAgent PATH via `os.environ.copy()` — if `opencode` isn't findable, every claim fails with exit 127 → 0-byte agent log → exit=None (indistinguishable from model or binary errors). Fix: `ln -sf ~/.opencode/bin/opencode ~/.local/bin/opencode` AND set `opencode_path: /Users/stephen/.opencode/bin/opencode` in runner.yaml. Verify with `env -i PATH=<LaunchAgent-PATH> ... opencode run --dir <worktree> -m <model> 'say yes'` before enabling the daemon. Observed: sjbmbp (2026-06-11, 5 aborts).

2. **model_map is mandatory for opencode-* lanes:** EVERY runner serving opencode-* lanes MUST have an explicit `model_map` to `fireworks/...` in `runner.yaml`. Without it, opencode resolves to opencode.ai-hosted models and hits their billing (Insufficient balance, 0-byte log, instant abort). See the runner.yaml example above. Observed gap: runner-2 (2026-06-10), sjbmbp (2026-06-11).

3. **Claude CLI is optional per host:** ~~The `claude` model requires macOS Claude.app~~ — OUTDATED. The claude CLI runs fine on Linux (yesod-runner serves the claude-fable-5 lane). Install it only on hosts meant to serve that lane, and configure gateway auth per the "Claude lane auth" section above. Hosts without it should not list claude/claude-fable-5 in their runner.yaml `models`.
2. **Path Compatibility:** `/Users/stephen` is symlinked to `/home/stephen` to match macOS paths.
3. **Beads Backup:** Backup git repo is at `/var/tmp/yesod-aicoe-beads-autobackup` (not a persistent remote).

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
journalctl -u yesod-codefactory-dispatch.service -f

# Check environment
sudo -u stephen env | grep -E "YESOD|FIREWORKS"

# Restart service
sudo systemctl restart yesod-codefactory-dispatch.service
```

### Beads Permission Issues
```bash
# Fix ownership
sudo chown -R stephen:stephen /home/stephen/dev5/yesod-aicoe/.beads/
chmod -R u+rw /home/stephen/dev5/yesod-aicoe/.beads/

# Restart service
sudo systemctl restart yesod-codefactory-dispatch.service
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql postgresql://stephen:lj*123NM@yesod-postgres-server:5432/stephen

# Check hosts file
cat /etc/hosts | grep yesod-postgres
```

---

## Maintenance Commands

```bash
# Update opencode
sudo dpkg -i /path/to/new-opencode.deb

# Update yesod
cd ~/dev5/yesod-aicoe/yesod
uv pip install -e .

# Update beads
bd version  # Check current
# Reinstall via official script if needed

# View service logs
sudo journalctl -u yesod-codefactory-dispatch.service

# View runner output
sudo tail -f /tmp/yesod-codefactory-dispatch.out
sudo tail -f /tmp/yesod-codefactory-dispatch.err
```

---

## Related Systems

- **Primary Runner:** `pompom` (macOS, 192.168.0.xxx)
- **PostgreSQL Server:** `yesod-postgres-server` (192.168.0.155:5432)
- **Proxmox Node:** `seykhl` (192.168.0.202)

---

## File Locations Summary

| File | Path |
|------|------|
| Runner Config | `~/.config/yesod/runner.yaml` |
| Environment | `/etc/yesod/runner.env` |
| Systemd Service | `/etc/systemd/system/yesod-codefactory-dispatch.service` |
| OpenCode Config | `~/.opencode.json` |
| Alternative OC Config | `~/.config/opencode/opencode.json` |
| Beads Config | `~/dev5/yesod-aicoe/.beads/config.yaml` |
| Yesod Source | `~/dev5/yesod-aicoe/yesod/` |
| Worktree Base | `/tmp/yesod-workdir/` |
| Beads Backup | `/var/tmp/yesod-aicoe-beads-autobackup/` |
| Service Logs | `/tmp/yesod-codefactory-dispatch.out` |
| Service Errors | `/tmp/yesod-codefactory-dispatch.err` |
| opencode Binary | `/usr/bin/opencode` |
| bd Binary | `/usr/local/bin/bd` |
| uv Binary | `/home/stephen/.local/bin/uv` |

---

## Quick Reference

```bash
# SSH to any runner
ssh stephen@yesod-runner        # 192.168.0.152
ssh stephen@yesod-runner-2      # 192.168.0.148
ssh stephen@yesod-runner-3      # 192.168.0.136

# Check status
export YESOD_POSTGRES_DSN=postgresql://stephen:lj*123NM@yesod-postgres-server:5432/stephen
yesod codefactory-dispatch status

# Restart service
sudo systemctl restart yesod-codefactory-dispatch.service

# Check all runners
psql $YESOD_POSTGRES_DSN -c "SELECT id, status, current_tasks, max_concurrent FROM runners;"

# Test opencode
opencode -p "Say hello" -q

# Create new runner from template
ssh seykhl "qm clone 109 <new_id> --name yesod-runner-N --full"
```
