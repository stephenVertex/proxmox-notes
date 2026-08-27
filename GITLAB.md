# GitLab: `makor.meshcrawler.com`

**Status:** deployed; ready for initial administrator setup and pilot projects.

**Last verified:** 2026-08-27

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
| Firewall | UFW default-deny inbound; SSH from `192.168.0.0/24` only |
| Tailscale | Not installed; it is optional for later private administration |

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

## Initial administrator actions

New-user sign-up is disabled. The `root` bootstrap password remains in
`/etc/gitlab/initial_root_password` only for GitLab's short initial-password
window. Retrieve it privately from the LAN, sign in, and immediately set and
vault a new password:

```bash
ssh stephen@192.168.0.170 'sudo cat /etc/gitlab/initial_root_password'
```

Before inviting other users:

1. Create named administrator accounts and stop using `root` for routine work.
2. Fastmail SMTP is configured with a dedicated app password; a delivery test
   to `gitlab@meshcrawler.com` succeeded on 2026-08-27. Test invitation and
   password-reset delivery after creating the named administrator accounts.
3. Enroll administrator 2FA, store recovery codes safely, then require 2FA
   according to the chosen policy. Instance-wide 2FA enforcement is **not**
   configured yet.
4. Review project visibility defaults, protected-branch policy, and
   personal-access-token expiry policy.
5. Create pilot projects under the private top-level `meshcrawler` group. Do
   not migrate existing GitHub projects until their owner accepts the pilot.

## GitLab Runner

| Component | Live configuration |
|---|---|
| Runner VM | VM 120, `makor-runner-docker-1`, Debian 13, `192.168.0.171` |
| Allocation | 6 vCPU (`host`), 16 GiB fixed RAM, 120 GiB disk, `onboot: 1`, QEMU guest agent |
| Packages | Docker Engine 29.7.2; GitLab Runner 19.3.1-1 |
| Scope | `meshcrawler` group runner, ID 1 |
| Tags | `linux-amd64`, `docker`; `run_untagged = false` |
| Capacity | `concurrent = 2` |
| Executor | Docker, default image `alpine:3.23`, pull policy `if-not-present` |
| Isolation | `privileged = false`; no host Docker socket or production credentials are mounted into jobs |
| Firewall | UFW default-deny inbound; SSH from `192.168.0.0/24` only |

The runner uses Cloudflare DNS resolvers (`1.1.1.1`, `1.0.0.1`), because the
LAN router had cached a negative result immediately after the new hostname was
created. Runner registration, GitLab handshake, and an unprivileged Docker
`alpine:3.23` smoke run have passed.

Do not put a runner authentication token in a repository or CI variable. It is
stored only in the runner's root-owned `/etc/gitlab-runner/config.toml`.

Create a separate protected deployment runner if pipelines later need LAN or
production credentials. General build runners must not receive them.

## Backups, recovery, and operations

The existing Proxmox job `sefer-light-services` now backs up both VMs daily at
03:30 to `nas-backups` using zstd snapshots. Retention is 7 daily, 4 weekly,
and 3 monthly backups.

This is useful VM-level protection, but a GitLab application backup schedule
and an encrypted off-VM copy of `/etc/gitlab/gitlab.rb` and
`/etc/gitlab/gitlab-secrets.json` are **not configured yet**. Before migrating
valuable projects, implement and test all of the following:

1. A daily `gitlab-backup create` that completes before the Proxmox backup.
2. An encrypted, least-privilege NAS or offsite copy of the GitLab archive,
   configuration, and secrets file.
3. An isolated restore rehearsal using the identical GitLab EE version.
4. Monitoring for data-disk capacity, Proxmox/GitLab backup failure, GitLab
   health, and the `cloudflared` systemd service.

Useful checks (none display credentials):

```bash
ssh stephen@192.168.0.170 'sudo gitlab-ctl status'
ssh stephen@192.168.0.170 'curl -fsS http://127.0.0.1/-/health'
ssh stephen@192.168.0.170 'sudo systemctl is-active cloudflared'
ssh stephen@192.168.0.171 'sudo gitlab-runner verify'
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
- VMs 119 and 120 are in the existing Proxmox backup job.

## Primary references

- [GitLab Linux package installation](https://docs.gitlab.com/install/package/)
- [GitLab backup and restore](https://docs.gitlab.com/administration/backup_restore/backup_gitlab/)
- [GitLab Runner registration](https://docs.gitlab.com/runner/register/)
- [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/setup/)
