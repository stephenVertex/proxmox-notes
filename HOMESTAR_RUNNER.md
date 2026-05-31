# homestar-runner — Self-Hosted GitHub Actions Runner

## Overview
`homestar-runner` (VMID 103) is a Debian 13 VM on Proxmox host `seykhl` running the GitHub Actions self-hosted runner agent for `stephenVertex/yesod-aicoe`.

## Why Self-Hosted?
- **Zero per-minute charges** — no GitHub Actions billing
- **Already on LAN/tailnet** — no need for Tailscale ephemeral joins in CI
- **Persistent state** — caches builds, tools, Docker layers between runs
- **Full control** over specs and environment

## VM Specifications
| Setting | Value |
|---------|-------|
| **VMID** | 103 |
| **Name** | homestar-runner |
| **OS** | Debian 13 "Trixie" (latest stable) |
| **CPU** | host (AVX passthrough) |
| **Cores** | 2 |
| **Memory** | 4GB |
| **Disk** | 30GB (raw on local-lvm) |
| **Network** | vmbr0 (bridge to LAN) |
| **Net Model** | virtio |
| **Display** | none (headless server) |

## Network Details
- **LAN IP**: 192.168.0.154 (DHCP)
- **MAC**: BC:24:11:6C:CF:B7
- **Hostname**: homestar-runner
- **DNS**: Added to local `/etc/hosts` on admin machines

## SSH Access
```bash
ssh stephen@homestar-runner
# or
ssh stephen@192.168.0.154
```

## GitHub Actions Runner

### Registration
- **Repository**: `https://github.com/stephenVertex/yesod-aicoe`
- **Runner Name**: `homestar-runner`
- **Runner ID**: 2
- **Pool**: Default
- **Labels**: `self-hosted`, `Linux`, `X64`, `homestar`
- **Version**: 2.334.0 (latest)

### Installation Location
```
/home/stephen/actions-runner/
├── bin/                          # Runner binaries
├── externals/                      # Node.js runtime
├── _work/                          # Job working directory
├── runsvc.sh                       # Service wrapper script
├── config.sh                       # Configuration script
├── run.sh                          # Interactive runner script
└── .runner                         # Registration config
```

### Systemd Service
```ini
[Unit]
Description=GitHub Actions Runner for yesod-aicoe
After=network-online.target

[Service]
ExecStart=/home/stephen/actions-runner/runsvc.sh
User=stephen
WorkingDirectory=/home/stephen/actions-runner
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=5min

[Install]
WantedBy=multi-user.target
```

### Service Commands
```bash
# Check status
sudo systemctl status actions.runner.yesod-aicoe.service

# Start/stop/restart
sudo systemctl start actions.runner.yesod-aicoe.service
sudo systemctl stop actions.runner.yesod-aicoe.service
sudo systemctl restart actions.runner.yesod-aicoe.service

# View logs
sudo journalctl -u actions.runner.yesod-aicoe.service -f
```

## Using This Runner in Workflows

### Default Labels
The runner automatically has these labels:
- `self-hosted`
- `Linux`
- `X64`

### Example Workflow (using self-hosted label)
```yaml
name: CI

on: [push, pull_request]

jobs:
  build:
    runs-on: self-hosted  # Uses any self-hosted runner
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: echo "Running on homestar-runner!"
```

### Targeting This Specific Runner (homestar label)
```yaml
name: CI on homestar

on: [push]

jobs:
  build:
    runs-on: homestar  # Only runs on homestar-runner
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: echo "Running specifically on homestar-runner!"
```

### Adding Custom Labels
You can add custom labels when configuring the runner:
```bash
./config.sh --unattended --url <url> --token <token> --labels homestar,proxmox
```

### Registration Command (with labels)
```bash
./config.sh --unattended --url https://github.com/stephenVertex/yesod-aicoe --token TOKEN --labels self-hosted,Linux,X64,homestar --name homestar-runner
```

Or from GitHub UI: Repo → Settings → Actions → Runners → homestar-runner → Labels

## Troubleshooting

### Runner Shows Offline
```bash
# Restart the service
sudo systemctl restart actions.runner.yesod-aicoe.service

# Check logs
sudo journalctl -u actions.runner.yesod-aicoe.service --no-pager
```

### Journal Errors
The serial-getty service was disabled to prevent spam:
```bash
sudo systemctl stop serial-getty@ttyS0
sudo systemctl disable serial-getty@ttyS0
```

Corrupted journal files were cleaned:
```bash
sudo rm -f /var/log/journal/*/user-1000@*.journal~
sudo systemctl restart systemd-journald
```

### Re-registering
If you need to re-register (e.g., token expired):
```bash
cd ~/actions-runner
./config.sh remove
# Then re-run with new token
./config.sh --unattended --url https://github.com/stephenVertex/yesod-aicoe --token NEW-TOKEN
```

## Resources
- Proxmox Host: `seykhl` (192.168.0.202)
- Cloud Image: `/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2`
- VM Disk: `local-lvm:vm-103-disk-0`
- GitHub Actions Runner Releases: https://github.com/actions/runner/releases
- GitHub Self-Hosted Runners Docs: https://docs.github.com/en/actions/hosting-your-own-runners

## Notes
- CPU type `host` is critical for modern tool compatibility
- The runner auto-updates when GitHub releases new versions
- For auto-scaling, consider using ephemeral runners (`--ephemeral` flag)
