# GitLab: `makor.meshcrawler.com`

Live recheck: GitLab local health reports `GitLab OK`, public HTTPS returns
200, cloudflared is active, and GitLab Runner ID 1 is online and accepts
untagged jobs (`linux-amd64`, `docker`; concurrent capacity 2). Both VMs
remain on Sefer `vmbr0` at `.170` and `.171`; the host has an additional
VLAN address as described in [NETWORK.md](NETWORK.md). Native backup service
completed successfully on September 5 at 01:31 Pacific. The configured nightly VM backup is not a clean success: September 5 archive transfer completed but NAS pruning failed. See [BACKUPS.md](BACKUPS.md).

**Status:** operational. The private `meshcrawler` group, `stevejb`
administrator account, outbound email, GitLab API/CLI access, and Docker CI
runner are all in use.

**Last verified:** 2026-09-22 for Tailscale, Git SSH, and local/public health;
2026-09-05 for the remaining deployment checks

## Service summary

`makor` is a single-node GitLab EE installation operated at the Free tier. It
publishes the web UI, API, Git-over-HTTPS, webhooks, and runner traffic through
an outbound Cloudflare Tunnel. No router port-forward, public Git SSH endpoint,
or Tailscale Funnel is used.

```text
Git clients and GitLab Runner
             |
https://makor.meshcrawler.com
             |
      Cloudflare Tunnel
             |
cloudflared on makor -> 127.0.0.1:80 GitLab NGINX
```

This is not a high-availability deployment: `sefer` is one Proxmox host and
GitLab, PostgreSQL, Redis, and Gitaly run in the same guest. Gitaly is GitLab's
internal repository-storage service; it is bundled with GitLab and is not a
separate VM to administer.

## Deployed infrastructure

| Component | Live configuration |
|---|---|
| GitLab VM | VM 119, `makor`, Debian 13, `192.168.0.170` |
| VM allocation | 8 vCPU (`host`), 24 GiB fixed RAM, `onboot: 1`, QEMU guest agent |
| Disks | 80 GiB OS disk; 300 GiB ext4 data disk mounted at `/var/opt/gitlab` |
| GitLab package | `gitlab-ee` 19.3.1-ee.0 |
| Outbound email | Fastmail SMTP from `gitlab@meshcrawler.com`; credentials use GitLab's encrypted SMTP secret store |
| Public URL | `https://makor.meshcrawler.com` |
| Tunnel | `makor`, ID `ffdf5860-2735-4fe8-89b0-e0ad6c5582e5` |
| Tunnel service | `cloudflared` 2026.8.2, enabled as a system service |
| DNS | Proxied CNAME to `ffdf5860-2735-4fe8-89b0-e0ad6c5582e5.cfargotunnel.com` |
| GitLab listener | Bundled NGINX on `127.0.0.1:80` only; Cloudflare terminates public TLS |
| Firewall | UFW default-deny inbound; SSH from `192.168.0.0/24` and on `tailscale0`; UDP 41641 on `eth0` |
| Tailscale | 1.102.4; `makor.tailb4b58.ts.net`; `100.126.58.74`; enabled at boot |

The VM address is statically provisioned through cloud-init. A router DHCP
reservation or exclusion has not yet been recorded, so do not assign
`192.168.0.170` to another device.

GitLab's initial configuration is in `/etc/gitlab/gitlab.rb`; the tunnel
configuration is root-readable only at `/etc/cloudflared/config.yml`. Tunnel
credentials are root-readable only and must never be placed in this repository
or copied into shell history.

## Public-route policy

- The main GitLab application is public at the HTTPS hostname and uses
  Git-over-HTTPS. Public Git-over-SSH is intentionally not offered.
- Cloudflare Tunnel ingress returns 404 for `/-/metrics`, `/-/health`,
  `/-/liveness`, and `/-/readiness` paths. Local health verification remains
  available at `http://127.0.0.1/-/health` on `makor`.
- No Cloudflare Access policy is in front of the hostname, because it would
  require deliberate testing of Git HTTPS and runner authentication flows.
- A Cloudflare cache-bypass rule, WAF policy, and authentication-path rate
  limit have not been configured in the dashboard yet. Add and test them before
  exposing the service to untrusted users.
- Treat uploads near or above 100 MB as unsupported until the actual
  Cloudflare-zone plan and end-to-end Git/LFS/artifact behavior are confirmed.
  The tunnel is appropriate for normal source repositories and small CI output,
  not a large-artifact transport design.

## Access and project creation

New-user sign-up is disabled. `stevejb` is the routine administrator and an
Owner of the private `meshcrawler` group; retain `root` only as a break-glass
account. The bootstrap password file is useful only during GitLab's short
initial-password window and must not be relied on for future access.

Fastmail SMTP is configured with a dedicated app password. A delivery test to
`gitlab@meshcrawler.com` succeeded on 2026-08-27.

Create projects under the private top-level `meshcrawler` group. In the web
UI, choose **New project** → **Create blank project**, select the group, and
choose **Private** visibility.

For an administrator workstation, the GitLab CLI is available through `glab`:

```bash
brew install glab
glab auth login --hostname makor.meshcrawler.com
GITLAB_HOST=makor.meshcrawler.com \
  glab repo create meshcrawler/my-new-repo --private --defaultBranch main
```

Use a personal access token with `api` and `write_repository` scopes when the
CLI requests one. `glab` stores the token in the macOS keychain. Do not put
tokens, runner authentication tokens, or SMTP credentials in a repository,
CI variable, or shell history. Clone and push repositories using their
Git-over-HTTPS URLs, or use private Git-over-SSH while connected to the tailnet.

## Private Git SSH over Tailscale

Makor joined `tailb4b58.ts.net` on 2026-09-22. Its addresses are
`100.126.58.74` and `fd7a:115c:a1e0::b22e:3a4b`, with MagicDNS name
`makor.tailb4b58.ts.net`. The existing OpenSSH service on TCP 22 authenticates
GitLab users with their registered public keys. The separate Tailscale SSH
feature is disabled. Public HTTPS continues through Cloudflare Tunnel.

Stephen's Mac applies the same SSH settings to the full hostname and the alias:

```sshconfig
Host makor-git makor.tailb4b58.ts.net
    HostName makor.tailb4b58.ts.net
    HostKeyAlias 192.168.0.170
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

`HostKeyAlias` preserves the VM's host keys already trusted under its LAN
address. The existing macOS keychain/agent options remain configured.
On another tailnet client, use the full hostname and a key registered with
GitLab; GitLab's public hostname does not carry SSH through Cloudflare.

```bash
ssh -T git@makor.tailb4b58.ts.net
git clone git@makor.tailb4b58.ts.net:meshcrawler/proxmox-notes.git
# The existing alias remains compatible:
git clone git@makor-git:meshcrawler/proxmox-notes.git
```

Tailscale was installed from its stable Debian `trixie` APT repository and
authenticated through the administrator's browser. The saved settings are:

```bash
tailscale up --hostname=makor --accept-dns=false --ssh=false --netfilter-mode=off
```

The VM keeps its existing DNS configuration and advertises no subnet or exit
node routes. `netfilter-mode=off` deliberately leaves filtering to UFW:
Tailscale's automatic interface ACCEPT rule would otherwise bypass UFW and
expose other listeners. The added rules are:

```bash
ufw allow in on tailscale0 to any port 22 proto tcp comment 'Git SSH over Tailscale'
ufw allow in on eth0 to any port 41641 proto udp comment 'Tailscale WireGuard'
```

Verification on 2026-09-22: SSH returned `Welcome to GitLab, @stevejb!`, and
`git ls-remote` retrieved the private repository HEAD through `makor-git`.
GitLab local health returned `GitLab OK`, and public sign-in HTTPS returned
200. TCP 22 was reachable over the tailnet; TCP 80, 8060, and 9094 timed out.
`tailscaled` is active and enabled at boot. The enrolled node key has
the tailnet's default expiry, currently 2027-03-21; manage renewal or disable
expiry for this server through the Tailscale admin console.

To withdraw the private route, run `tailscale down` on makor and change the
Mac alias's `HostName` back to `192.168.0.170` for LAN SSH access.

## Dual-remote migration

`proxmox-notes` is mirrored to both GitHub and GitLab while the self-hosted
service is being proven. The existing `origin` remote remains GitHub; the
secondary remote is named `gitlab` and points at
`git@makor.tailb4b58.ts.net:meshcrawler/proxmox-notes.git`.

The yesod process `makor-gitlab-remote-access` uses this explicit Tailscale
hostname for Git SSH. Its API/CLI steps always set
`GITLAB_HOST=makor.meshcrawler.com`: the SSH remote hostname must not be used
to infer the HTTPS/API endpoint.

On Stephen's administrator Mac, `makor-git` now targets
`makor.tailb4b58.ts.net`. GitLab has the Mac's `id_ed25519` public key
registered for `stevejb`. Existing remotes using this alias work wherever
the Mac is connected to the tailnet. Git-over-HTTPS remains available through
the public Cloudflare hostname.

Push new work to both while this transition is active:

```bash
git push origin main
git push gitlab main
git push gitlab --tags
```

Do not retire GitHub or make GitLab the sole canonical copy until GitLab
application backups and a restore rehearsal have been completed successfully.

Still to complete before inviting untrusted users:

1. Verify administrator 2FA enrollment and recovery codes, then decide
   whether to enforce instance-wide 2FA.
2. Test invitation and password-reset messages after creating additional
   accounts.
3. Review project visibility defaults, protected-branch policy, and
   personal-access-token expiry policy.

## GitLab Runner

| Component | Live configuration |
|---|---|
| Runner VM | VM 120, `makor-runner-docker-1`, Debian 13, `192.168.0.171` |
| Allocation | 6 vCPU (`host`), 16 GiB fixed RAM, 120 GiB disk, `onboot: 1`, QEMU guest agent |
| Packages | Docker Engine 29.7.2; GitLab Runner 19.3.1-1 |
| Scope | `meshcrawler` group runner, ID 1 |
| Tags | `linux-amd64`, `docker`; `run_untagged = true` (the runner also accepts untagged jobs from the trusted `meshcrawler` group) |
| Capacity | `concurrent = 2` |
| Executor | Docker, default image `alpine:3.23`, pull policy `if-not-present` |
| Isolation | `privileged = false`; no host Docker socket or production credentials are mounted into jobs |
| Firewall | UFW default-deny inbound; SSH from `192.168.0.0/24` only |

The runner uses Cloudflare DNS resolvers (`1.1.1.1`, `1.0.0.1`), because the
LAN router had cached a negative result immediately after the new hostname was
created. Runner registration, GitLab handshake, and an unprivileged Docker
`alpine:3.23` smoke run have passed. The runner also picked up the first
untagged project job successfully.

Do not put a runner authentication token in a repository or CI variable. It is
stored only in the runner's root-owned `/etc/gitlab-runner/config.toml`.

Create a separate protected deployment runner if pipelines later need LAN or
production credentials. General build runners must not receive them.

## Backups, recovery, and operations

The existing Proxmox job `sefer-light-services` backs up both GitLab VMs daily
at 03:30 to `nas-backups` using zstd snapshots. Retention is 7 daily, 4
weekly, and 3 monthly backups.

In addition, `sefer` now creates GitLab-native recovery artifacts daily at
01:30, leaving a two-hour buffer before the Proxmox snapshot. The root-owned
`gitlab-app-backup.timer` invokes `/usr/local/sbin/backup-gitlab-to-nas`, whose
tracked source is [`scripts/backup-gitlab-to-nas`](scripts/backup-gitlab-to-nas).
The service:

1. Runs `gitlab-backup create` on `makor`.
2. Runs `gitlab-ctl backup-etc` to include `gitlab.rb`,
   `gitlab-secrets.json`, certificates, and other `/etc/gitlab` configuration.
3. Copies both archives atomically over a dedicated restricted SSH key, checks
   their SHA-256 hashes, then removes the temporary guest copies.
4. Retains each artifact type for 35 days on the NAS.

The Proxmox host, rather than the GitLab VM, writes to the NAS. This keeps the
NAS SMB credential out of the GitLab guest. The archive paths on the mounted
NAS share are:

```text
/mnt/proxmox-backups/gitlab/makor/application/
/mnt/proxmox-backups/gitlab/makor/configuration/
```

Two full backup runs succeeded on 2026-08-27. Each application archive and its
configuration archive was checksum-verified after transfer; the initial pair
also passed a local `tar` integrity listing. The container registry is disabled
on this GitLab instance, so there are no registry images to protect.

The NAS copies are not separately encrypted by this process. Before retiring
GitHub or treating GitLab as the sole canonical copy of valuable projects,
complete an isolated restore rehearsal using the exact GitLab EE version and
decide on encrypted, access-controlled storage for the application and
configuration archives. Also add monitoring/alerting for data-disk capacity,
Proxmox/GitLab backup failure, GitLab health, and `cloudflared`.

Useful checks (none display credentials):

```bash
ssh stephen@192.168.0.170 'sudo gitlab-ctl status'
ssh stephen@192.168.0.170 'curl -fsS http://127.0.0.1/-/health'
ssh stephen@192.168.0.170 'sudo systemctl is-active cloudflared'
ssh stephen@192.168.0.171 'sudo gitlab-runner verify'
ssh root@sefer 'systemctl status --no-pager gitlab-app-backup.timer'
ssh root@sefer 'journalctl -u gitlab-app-backup.service -n 50 --no-pager'
```

For an upgrade, take and verify an application backup first, apply the newest
supported patch release in the intended GitLab release line, wait for
background migrations, and follow GitLab's required upgrade stops. A Proxmox
snapshot aids rollback but does not replace a tested application restore.

## Verified at deployment

- GitLab services are up and the local health endpoint reports `GitLab OK`.
- `makor.meshcrawler.com` returns HTTPS GitLab sign-in traffic through the
  dedicated Tunnel; it does not expose GitLab's local listener directly.
- Public metrics and health endpoints return 404 at the Tunnel; normal sign-in
  remains reachable.
- The runner is online, verified by GitLab, and can run the pinned Alpine image
  unprivileged.
- Fastmail accepted GitLab's SMTP verification message sent from
  `gitlab@meshcrawler.com`.
- Native application and configuration backups completed twice, were
  SHA-256-verified on `nas-backups`, and are scheduled daily at 01:30.
- Private project `meshcrawler/yesod-semantic-graph` was created with `main`
  as its default branch. Its first CI job pulled the `uv` Docker image, checked
  out the repository through Gitaly, and ran formatting, linting, type checks,
  and 14 tests successfully on runner 1. The final `uv build` step failed
  because the project source distribution included its generated `.venv`; this
  is a project packaging configuration issue, not a GitLab or runner failure.
- VMs 119 and 120 are in the existing Proxmox backup job.

## Primary references

- [GitLab Linux package installation](https://docs.gitlab.com/install/package/)
- [GitLab backup and restore](https://docs.gitlab.com/administration/backup_restore/backup_gitlab/)
- [GitLab Runner registration](https://docs.gitlab.com/runner/register/)
- [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/setup/)
