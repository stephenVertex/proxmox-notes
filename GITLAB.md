# Plan: GitLab on `sefer` (`makor.meshcrawler.com`)

**Status:** proposed design — no VM, DNS record, tunnel, credentials, or GitLab
installation has been created.

**Last verified:** 2026-08-27

## Objective and design

Run a single-node, self-managed GitLab Free instance on a dedicated Debian 13 VM
on `sefer`. Publish its web UI, API, Git-over-HTTPS, and CI traffic at
`https://makor.meshcrawler.com` through a dedicated Cloudflare Tunnel, using the
same outbound-only pattern as n8n, DocuSeal, and draw.io.

```text
Developers, Git clients, and GitLab Runners
                |
         HTTPS makor.meshcrawler.com
                |
           Cloudflare edge
                |
  outbound Cloudflare Tunnel (cloudflared in makor VM)
                |
    127.0.0.1:80 GitLab bundled NGINX -> GitLab services
```

The Cloudflare Tunnel, not Tailscale Funnel, is the public reverse tunnel. No
router port-forward or public IP is required. Tailscale is optional and is only
for private administration (SSH) and, if needed later, Git-over-SSH for trusted
tailnet users.

This is deliberately a single-node service, not a high-availability GitLab
deployment. `sefer` is itself one Proxmox node, so host failure still causes an
outage. The design provides recoverability through application backups and the
existing Proxmox NAS backups; it does not claim host-level HA.

## Confirmed environment and proposed allocation

At planning time, `sefer` has 88 logical CPUs, 251 GiB installed RAM (about
218 GiB available), and about 840 GiB free on the `vmdata` ZFS mirror. GitLab's
current single-node baseline is 8 vCPU and 16 GiB RAM. The allocation below
leaves room for the migrated services and runners while avoiding contention with
GitLab's database, Redis, Gitaly, Puma, and Sidekiq processes.

| Item | Proposed value | Rationale |
|---|---|---|
| VMID / hostname | `119` / `makor` (confirm VMID is unused when creating) | Next service VM identifier; clear service name |
| Guest OS | Debian 13 cloud image | Matches current service VM standard |
| CPU | 8 vCPU, `cpu: host` | GitLab single-node baseline |
| Memory | 24 GiB fixed, ballooning disabled | Healthy headroom above GitLab's 16 GiB baseline; predictable latency |
| OS disk | 80 GiB on `vmdata` | OS, package, journals, and operating overhead |
| GitLab data disk | 300 GiB on `vmdata`, mounted at `/var/opt/gitlab` before installation | Isolates repositories, database, artifacts, LFS, and backups from `/` |
| Network | VirtIO on `vmbr0`; DHCP reservation instead of an unrecorded static address | Stable LAN identity without collision risk |
| Proxmox settings | QEMU guest agent, serial console, boot order, `onboot: 1`, `virtio-scsi-single` | Conforms to current Debian service VMs |

The 380 GiB provisioned footprint fits within the current pool capacity, but
ZFS thin provisioning is not capacity planning: alert at 70% and 80% use of the
data disk, and do not let repository, artifact, package, or Docker cache growth
consume the pool's recovery headroom.

## Scope and initial product boundary

Initial production scope:

- GitLab web UI, API, webhooks, Git-over-HTTPS, issues, CI/CD, project/group
  variables, and small Git LFS usage.
- One trusted Docker-executor group runner, with a second separate runner only
  after measured demand.
- Local GitLab PostgreSQL, Redis, Gitaly, artifacts, packages, and LFS storage
  on the dedicated data disk.

Explicitly defer these features until separately designed and tested:

- Container Registry. It needs a second hostname and image upload paths; do not
  quietly enable it behind the main GitLab route.
- GitLab Pages, GitLab Kubernetes Agent, object storage, SAML/OIDC, and
  external PostgreSQL.
- Public Git-over-SSH. Cloudflare Tunnel public-hostname routing is HTTP(S), not
  ordinary public SSH. HTTPS cloning is the standard public path. A documented
  Tailscale-only SSH alias can be added later for trusted users if required.
- Large Git pushes, LFS objects, artifacts, and package uploads. Cloudflare Pro
  currently has a 100 MB maximum HTTP upload, which can return HTTP 413. Start
  with repositories and CI outputs well under that size; for larger payloads,
  use a Tailscale-only direct Git/transfer design, external object storage, or a
  Cloudflare plan/architecture change before relying on it.

## Implementation phases

### 0. Approve the operating choices

Before changing infrastructure, confirm these decisions:

1. The primary GitLab top-level group and initial administrators. Start with
   invitation-only accounts; do not enable public sign-up.
2. An `gitlab@meshcrawler.com` Fastmail mailbox or alias and a dedicated SMTP
   app password. GitLab must send invitations, password resets, and security
   notices before it is relied on.
3. Acceptance of the 100 MB Cloudflare Pro HTTP-upload limit for the pilot.
   If normal repositories or CI artifacts exceed it, design the private large
   transfer path first instead of discovering it during a migration.
4. Whether Tailscale administration uses a new `tag:gitlab` with an ACL limited
   to administrators. Never place a Tailscale auth key in this repository.
5. Which small, non-critical projects are the first migration pilot. Existing
   GitHub Actions runners on VM 103 remain unchanged.

### 1. Provision and harden the `makor` VM

1. Verify that VMID 119 and the chosen DHCP-reserved LAN address are free; clone
   or create the Debian 13 cloud-init VM with the allocation above.
2. Partition, format, and mount the second disk at `/var/opt/gitlab` using a
   UUID-based `/etc/fstab` entry before installing GitLab. Ensure the mount is
   present after a reboot.
3. Update the OS, install and verify `qemu-guest-agent`, create a non-root
   administrator, and use SSH keys only. Record the VM's LAN address in
   `README.md` once it exists.
4. Use a default-deny guest firewall. GitLab's bundled NGINX will bind only to
   loopback, so no LAN or Internet listener is needed for port 80/443. Permit
   SSH only over `tailscale0` if Tailscale is approved; Proxmox console remains
   the break-glass path.
5. Install Tailscale only for the approved private-administration use case.
   Tag and authorize it through the tailnet admin console, then verify its ACL
   from an administrator device. It is not part of the public web route.

### 2. Install and configure GitLab

Use the official Linux package (`gitlab-ee` running at the Free tier) rather
than a hand-assembled Docker Compose stack. Pin the current stable patch release
at install time, record it in the operational document, and use the same
edition for every restore.

Configure `/etc/gitlab/gitlab.rb` before the first production reconfigure with
the following intent (the exact package version's sample file remains the
implementation reference):

```ruby
external_url 'https://makor.meshcrawler.com'
letsencrypt['enable'] = false

# TLS terminates at Cloudflare; cloudflared reaches this listener locally.
gitlab_rails['nginx']['listen_addresses'] = ['127.0.0.1']
gitlab_rails['nginx']['listen_port'] = 80
gitlab_rails['nginx']['listen_https'] = false
gitlab_rails['nginx']['redirect_http_to_https'] = false
```

Then run `gitlab-ctl reconfigure`, verify all bundled services with
`gitlab-ctl status`, and check the local health endpoints before publishing the
route. Do not enable the bundled Let's Encrypt integration: Cloudflare supplies
the public certificate and the tunnel encrypts Cloudflare-to-VM traffic.

After first sign-in:

- Set and vault the initial `root` password, create named administrator accounts,
  and stop using `root` for routine work.
- Disable new-user sign-up, require confirmed email, set appropriate password
  and personal-access-token expiry policy, and enforce 2FA after the pilot
  administrators have verified recovery codes.
- Configure Fastmail SMTP using a dedicated app password stored in a root-owned
  secret file or the approved secret manager; test invitation and reset email.
- Disable Git-over-HTTPS password authentication once personal, deploy, and
  project access-token workflows have been tested.
- Leave the Container Registry, Pages, and public Git SSH disabled in this
  rollout.

### 3. Create the Cloudflare Tunnel and public route

1. In the Cloudflare dashboard, create a new named tunnel, `makor`, rather than
   reusing the n8n, DocuSeal, or draw.io connector.
2. Install `cloudflared` as a managed system service in the `makor` VM. Keep the
   tunnel token/credentials root-readable only and out of Git, shell history,
   backups with broad access, and this documentation.
3. Add the published application route:

   | Public hostname | Tunnel service |
   |---|---|
   | `makor.meshcrawler.com` | `http://127.0.0.1:80` |

   The dashboard creates the proxied `CNAME` to the tunnel UUID. Use the
   dashboard or an explicit cloudflared configuration; the local Mac
   cloudflared configuration is known to select the wrong tunnel if used
   without an explicit config override.
4. Add a cache rule to bypass caching for the entire hostname. Apply Cloudflare
   managed WAF protections and targeted rate limits for authentication paths,
   while testing Git clone/push, API, webhooks, and runner polling after each
   rule. Do not put Cloudflare Access in front of the first rollout: it can
   interrupt standard Git HTTPS and runner API requests unless service-token
   handling and bypasses are deliberately engineered and tested.
5. Confirm that the instance generates only `https://makor.meshcrawler.com`
   URLs, correctly accepts uploads under the limit, supports WebSockets, and
   does not redirect to a LAN IP or port.

### 4. Establish backup, recovery, monitoring, and upgrades

The existing `sefer-light-services` Proxmox job runs daily at 03:30 to
`nas-backups`, retaining 7 daily, 4 weekly, and 3 monthly copies. Add VM 119
only after GitLab passes the acceptance checks. A VM snapshot is useful but is
not the only GitLab recovery mechanism.

1. Schedule `gitlab-backup create` daily early enough to finish before the
   03:30 Proxmox backup. Store the result initially on the dedicated GitLab data
   disk, then copy it to a dedicated, least-privilege NAS/WORM path. Set a
   retention policy that is at least as long as the VM-backup policy and alert
   on either backup failure.
2. Back up `/etc/gitlab/gitlab.rb` and `/etc/gitlab/gitlab-secrets.json`
   separately, encrypted and access-controlled independently from the data
   archive. These secrets are required to restore encrypted CI variables, 2FA,
   and runner access.
3. Record the exact GitLab edition and version with each backup. Restore only
   onto a working instance of the identical GitLab version and edition, then
   restore configuration and secrets before accepting users.
4. Perform a full, isolated restore rehearsal before migration and at least
   quarterly thereafter. The acceptance target is a 24-hour RPO and a
   documented, tested four-hour RTO; revise those targets after the first
   rehearsal.
5. Feed VM resource, backup, tunnel-process, and GitLab health status into the
   existing SigNoz environment. Monitor the local `/-/health` liveness check
   and `health_check` comprehensive endpoint from an allowed local or tailnet
   monitor; do not expose metrics or health administration endpoints publicly.
6. Apply GitLab updates on a maintained monthly window: first create and verify
   an application backup, install the newest patch in the intended minor line,
   wait for background migrations, and follow all required upgrade stops for
   major/minor changes. A Proxmox snapshot is a rollback aid, not a replacement
   for a tested application restore.

### 5. Add dedicated GitLab runners

GitLab recommends runners be separate from the GitLab host. Do not install them
on `makor`, and do not repurpose VM 103's GitHub Actions runners without a
separate migration decision.

Provision the initial runner as follows:

| Item | Initial runner |
|---|---|
| VMID / hostname | `120` / `makor-runner-docker-1` (confirm VMID is unused) |
| Guest allocation | Debian 13; 6 vCPU; 16 GiB fixed RAM; 120 GiB `vmdata` disk; QEMU agent; `onboot: 1` |
| Runner scope | `meshcrawler` group runner, not instance-wide |
| Executor | Docker executor with a pinned default image |
| Initial capacity | `concurrent = 2`, then increase only after observing CPU, RAM, disk, and queue time |
| Tags | `linux-amd64`, `docker`, and workload-specific tags; `run_untagged = false` |
| Trust boundary | `privileged = false`; no host Docker socket or production credentials mounted into job containers |

Implementation details:

1. Install Docker Engine and GitLab Runner from their official repositories.
   Keep GitLab Runner compatible with the installed GitLab version.
2. In the GitLab UI, create a group runner and obtain its `glrt-` authentication
   token. Register non-interactively over `https://makor.meshcrawler.com`; keep
   the token only in the runner's root-owned configuration, never in a project
   variable or repository.
3. Use a default Docker image pinned to a tested version or digest, an isolated
   `/cache` volume, and a finite log/output limit. Allow only reviewed images
   and services as the project set stabilizes. Do not use `:latest` for trusted
   build inputs.
4. Create a separate protected deployment runner later if pipelines must access
   production credentials or the LAN. It should accept only protected refs and
   have narrowly scoped network/secret access. General build runners must never
   inherit those credentials.
5. Add one simple tagged pipeline that checks out a test project, runs in a
   pinned container image, and proves cache cleanup/retention. Add runner VM 120
   to the Proxmox backup job once that test is reliable.

### 6. Pilot, migration, and steady state

1. Create the top-level group, an internal test project, protected default
   branch rules, project roles, and a short contribution/CI template.
2. Import one small non-critical GitHub repository. Verify commit history,
   issues, CI variables, webhooks, clone/push over HTTPS, runner execution,
   and email notifications before moving a second project.
3. Keep GitHub as the source of truth until a project owner signs off on its
   GitLab migration. Do not bulk-import or change external links during the
   pilot.
4. After pilot acceptance, document actual VM IDs/IPs, tunnel UUID, backup
   location and retention, runner names/tags, current package version, recovery
   test date, and the approved Git SSH/large-payload policy in the live service
   documentation and domain registry.

## Acceptance checklist

- [ ] `makor` guest survives reboot with its data disk mounted and QEMU agent
      reporting healthy.
- [ ] The Cloudflare dashboard reports the dedicated tunnel healthy; the public
      hostname has valid HTTPS and GitLab emits no LAN/HTTP redirects.
- [ ] No port 80, 443, or Git SSH port is directly reachable on the LAN or
      Internet; only loopback receives cloudflared's upstream HTTP traffic.
- [ ] Named administrators can sign in, receive Fastmail notices, enroll 2FA,
      and use recovery codes.
- [ ] Invitation-only enrollment, token policy, project visibility defaults,
      and protected-branch settings have been checked by an administrator.
- [ ] HTTPS clone, push, API request, webhook, and a sub-100 MB upload work
      through Cloudflare. The team has explicitly accepted the large-upload
      policy.
- [ ] A tagged Docker job runs only on the new group runner; it is unprivileged
      and does not receive production credentials.
- [ ] `gitlab-backup create`, encrypted configuration/secrets backup, NAS copy,
      and Proxmox backup all complete successfully.
- [ ] An isolated full restore succeeds using the identical GitLab version and
      edition, and the runbook records elapsed recovery time.
- [ ] Alerts cover data-disk capacity, backup age/failure, `cloudflared`, and
      GitLab health.

## Recovery and rollback posture

Before the pilot, rollback is simply disabling the Cloudflare published route
and stopping the new service; no existing application is changed. After data is
migrated, recover into a new isolated VM with the same GitLab version/edition,
restore `/etc/gitlab/gitlab.rb` and `gitlab-secrets.json`, restore the
application backup, validate locally, then switch the Cloudflare route. Never
restore an application archive without its matching secrets file.

## Primary references

- [GitLab single-node installation requirements](https://docs.gitlab.com/install/requirements/)
- [GitLab Linux package installation](https://docs.gitlab.com/install/package/)
- [GitLab SSL termination and NGINX settings](https://docs.gitlab.com/omnibus/settings/ssl/)
- [GitLab backup and restore](https://docs.gitlab.com/administration/backup_restore/backup_gitlab/)
- [GitLab runner registration and Docker executor](https://docs.gitlab.com/runner/register/)
- [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/setup/)
- [Cloudflare Tunnel routing](https://developers.cloudflare.com/tunnel/routing/)
- [Cloudflare upload limits](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/)
