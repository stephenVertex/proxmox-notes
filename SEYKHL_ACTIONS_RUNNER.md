# seykhl-actions-runner — Self-Hosted GitHub Actions VM

**Last verified:** 2026-09-05. VM 103 remains on Sefer `vmbr0` at
`192.168.0.154`; Sefer also has VLAN address `192.168.20.10` (see
[NETWORK.md](NETWORK.md)). All five runner services are active. QEMU guest
agent queries fail; SSH works. The configured nightly VM backup is not a clean success: September 5 archive transfer completed but NAS pruning failed. See [BACKUPS.md](BACKUPS.md).

## Overview

`seykhl-actions-runner` (VMID 103) is a Debian 13 guest on the Proxmox host
`sefer`. It hosts repository-scoped GitHub Actions runner registrations. The
name `homestar` is reserved for the NAS and must not be used
for this VM, its GitHub runners, or workflow labels.

## VM specifications

| Setting | Value |
|---------|-------|
| VMID | 103 |
| Proxmox name / guest hostname | `seykhl-actions-runner` |
| OS | Debian 13 “Trixie” |
| CPU / memory | 2 host cores / 4 GB |
| Disk | 30 GB on `vmdata` |
| LAN | `192.168.0.154`, MAC `BC:24:11:6C:CF:B7` |

SSH by IP is canonical until LAN DNS/DHCP naming has propagated:

```bash
ssh stephen@192.168.0.154
```

## GitHub runner registrations

Five runner services were active at the 2026-09-05 inventory:

| Systemd service suffix | Runner name |
|---|---|
| `clip-together` | `seykhl-actions-clip-together` |
| `sjbis` | `seykhl-actions-sjbis` |
| `docs` | `seykhl-actions-docs` |
| `yesod` | `seykhl-actions-yesod` |
| `yesodwork` | `seykhl-actions-yesodwork` |

The local `.runner` files confirm all five repository registrations. Custom
labels below are the previously recorded labels; GitHub-side label and
busy/online state were not queried in this audit.

Each repository has its own runner directory and registration. Workflows
select purpose-specific labels; they do not select the VM hostname.

| Repository | Registration name | Custom labels | Directory |
|------------|-------------------|---------------|-----------|
| `stephenVertex/yesod-aicoe` | `seykhl-actions-yesod` | `yesod-ci` | `~/actions-runner` |
| `stephenVertex/clip-together` | `seykhl-actions-clip-together` | `dertog-deploy` | `~/actions-runner-clip-together` |
| `stephenVertex/sjbis` | `seykhl-actions-sjbis` | `linux-x64`, `sjbis-ci` | `~/actions-runner-sjbis` |
| `stephenVertex/yesod-aicoe-docs` | `seykhl-actions-docs` | Not reverified | `~/actions-runner-docs` |
| `stephenVertex/yesod.work` | `seykhl-actions-yesodwork` | Not reverified | `~/actions-runner-yesodwork` |

GitHub automatically adds the read-only `self-hosted`, `Linux`, and `X64`
labels to self-hosted registrations.

### Workflow routing

Use a capability label together with GitHub's default platform labels:

```yaml
runs-on: [self-hosted, Linux, X64, yesod-ci]
```

For Clip Together deployment:

```yaml
runs-on: [self-hosted, dertog-deploy]
```

For the Sjbis Linux release build:

```yaml
runs-on: [self-hosted, sjbis-ci]
```

Do not use `runs-on: homestar`; `homestar` is the NAS hostname, not an Actions
capability.

## Services and logs

```bash
# List all five registrations
systemctl list-units --type=service 'actions.runner.*'

# Follow one registration
sudo journalctl -u actions.runner.stephenVertex-yesod-aicoe.seykhl-actions-yesod.service -f
sudo journalctl -u actions.runner.stephenVertex-clip-together.seykhl-actions-clip-together.service -f
sudo journalctl -u actions.runner.stephenVertex-sjbis.seykhl-actions-sjbis.service -f
```

The runner work directories are persistent caches. Re-registering a runner
does not require deleting its `_work` directory.

## Safe rename or re-registration procedure

1. Add the replacement custom label through GitHub's runner-label API.
2. Update every consuming workflow and confirm the new label is accepted.
3. Wait until that repository's runner reports `busy: false`.
4. Stop and uninstall its service with `sudo ./svc.sh stop` and
   `sudo ./svc.sh uninstall`.
5. Run `./config.sh remove --token <remove-token>`.
6. Register the new name with a fresh registration token and all required
   custom labels.
7. Reinstall/start the service and verify GitHub reports it online.
8. Only then remove legacy labels.

Runner removal and registration tokens are short-lived and should be obtained
from the GitHub API immediately before use.

## Dertog access

This VM can reach dertog over the LAN and the registration contexts use
repository-scoped SSH material where required. For Yesod frontend deployment,
the intended execution path is the `yesod-ci` registration copying a verified,
content-addressed live-viz artifact to dertog. A successful deploy must verify
the publicly served asset hash, not merely an HTTP 200 response.

## Resources

- Proxmox host: `sefer` (`192.168.0.100`)
- VM disk: `vmdata:vm-103-disk-0`
- [GitHub self-hosted runner documentation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners)
- [GitHub runner releases](https://github.com/actions/runner/releases)
