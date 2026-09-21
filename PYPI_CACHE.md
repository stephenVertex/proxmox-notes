# Shared PyPI cache on Seykhl

Deployed and verified 2026-09-20. Endpoint:

```text
http://pypi.internal.yesod.work:3141/simple/
```

The service and package storage live on **Seykhl itself**, at
`192.168.20.202:3141`. Sefer has only the matching DNS record. Both LAN
resolvers return Seykhl's address. No VM, runner service, runner configuration,
or system Python environment was changed by this deployment.

## Opt in with environment variables

For pip:

```bash
export PIP_INDEX_URL=http://pypi.internal.yesod.work:3141/simple/
export PIP_TRUSTED_HOST=pypi.internal.yesod.work
python -m pip install -r requirements.txt
```

For uv (verified with uv 0.12.7):

```bash
export UV_DEFAULT_INDEX=http://pypi.internal.yesod.work:3141/simple/
export UV_INSECURE_HOST=pypi.internal.yesod.work
uv pip install -r requirements.txt
```

Alternatively, source [pypi-cache/client.env](pypi-cache/client.env) from a
runner shell or build job to set all four variables. Nothing sources it
automatically. The trusted/insecure-host settings allow HTTP to this specific
internal host; upstream downloads from public PyPI use verified HTTPS.
Clients need the LAN DNS resolvers and a route to VLAN 20.

The first request fetches a missing wheel, source archive, or metadata file
from public PyPI and saves it on Seykhl. Later clients download the same file
from Seykhl's disk. Keep pip/uv's normal local caches enabled too: those avoid
even the LAN download when the runner already has the package.

Use this as the default index, rather than adding it as an extra index.
Existing command-line options or project index configuration may override
these environment settings. Explicit artifact URLs, Git dependencies,
Python interpreter downloads, and non-PyPI dependencies do not automatically
pass through this cache. This is a public-PyPI cache, not a private package
upload registry or a complete mirror.

### Frozen and offline Yesod environments

An existing `uv.lock` can pin the public registry and artifact URLs. Setting
`UV_DEFAULT_INDEX` does not rewrite a frozen lockfile. Review an intentional
online lockfile update before expecting those installations to use the cache;
such a lockfile can then depend on this LAN endpoint. Do not rewrite production
locks merely to enable caching.

The inspected Yesod provisioning source uses `UV_NO_CONFIG=1`, with
`UV_OFFLINE=1`/`--offline` and `--frozen` for immutable release staging;
gate execution also uses `uv run --offline --frozen`. Offline clients never
contact this proxy. Their baked dependency environments were preserved.
The cache is available for opt-in online installs and future build integration.

To stop opting in for a shell or job:

```bash
unset PIP_INDEX_URL PIP_TRUSTED_HOST UV_DEFAULT_INDEX UV_INSECURE_HOST
```

This restores whatever other client configuration applies. There is no
automatic direct-PyPI failover if Seykhl is unavailable.

## Service and storage

| Setting | Deployed value |
| --- | --- |
| Service | `pypi-cache.service`, enabled on Seykhl |
| Implementation | Dedicated Nginx 1.26.3 instance, Debian package `1.26.3-3+deb13u9` |
| Configuration | `/etc/pypi-cache/nginx.conf` |
| Disk cache | `/var/cache/pypi-cache/objects`, on Seykhl's root filesystem |
| Cache policy | 10 GiB target, evict when filesystem free space falls below 20 GiB, 30-day inactivity expiry |
| Index freshness | 5-minute cache TTL; stale responses can be used on upstream errors |
| Artifact freshness | Honor upstream immutable/cache headers; 30-day fallback TTL |
| Client access | Loopback, `192.168.20.0/24`, `192.168.0.0/24`; listeners only on loopback and `.20.202` |
| Upstreams | Only `pypi.org` and `files.pythonhosted.org`, TLS verification enabled |
| Resource limits | Dynamic unprivileged user, 512 MiB memory, 200% CPU quota, nice 5 |
| Logs | System journal for `pypi-cache.service` |

Nginx evicts asynchronously: the size/free-space values are eviction targets,
not a hard filesystem quota. Concurrent downloads can temporarily exceed them.
At deployment Seykhl had about 38 GiB free on its 68 GiB root filesystem.
No space was allocated on Sefer or either host's VM storage pools.

Systemd manages the cache directory (backed by `/var/cache/private/pypi-cache`
with `DynamicUser`) and retains it across service restarts. Cache contents are
disposable, so they are not added to backups. The package's default
`nginx.service` is masked; it does not claim ports 80 or 443.

HTML and PEP 691 JSON index responses rewrite artifact URLs to this endpoint,
preserving hashes and metadata. The artifact cache is shared between pip and
uv, supports range responses, and serializes concurrent fills of the same key.
`X-PyPI-Cache: HIT` and journal entries with `cache=HIT upstream_time=-` identify
responses served locally. `/healthz` checks the local listener, not upstream
PyPI reachability.

## Deployment and operations

Sources: [Nginx configuration](pypi-cache/nginx.conf),
[systemd unit](systemd/pypi-cache.service), and
[DNS inventory](dns/infra.hosts).

```bash
bash scripts/deploy-pypi-cache.sh
bash scripts/deploy-pypi-dns.sh
```

The service deployer defaults to `root@seykhl`, verifies its `.20.202` address,
installs only the Nginx packages if missing, and backs up configuration under
`/etc/pypi-cache-before.*`. It validates and starts the service as the
unprivileged service user. Failed updates restore the prior configuration.

The DNS deployer checks that live inventories match the repository before
adding the alias. It refuses unrelated drift, saves `infra.hosts.before-pypi.*`
copies, and reloads dnsmasq host records without restarting DHCP. It touches
neither DHCP configuration nor leases. Future full DNS deployments must retain
the PyPI record in `dns/infra.hosts`.

```bash
ssh -o BatchMode=yes root@seykhl 'systemctl status pypi-cache --no-pager'
ssh -o BatchMode=yes root@seykhl 'journalctl -u pypi-cache -n 50 --no-pager'
ssh -o BatchMode=yes root@seykhl 'du -sh /var/cache/pypi-cache/objects; df -h /'
curl -fsS http://pypi.internal.yesod.work:3141/healthz
```

To disable the cache, remove clients' opt-in settings first, then run
`systemctl disable --now pypi-cache.service` on Seykhl. This leaves the cache
and configuration available for recovery. Restore a known-good configuration
and unit from the deployment backup, run `systemctl daemon-reload`, then
`systemctl enable --now pypi-cache.service` to recover. No hypervisor or runner
restart is needed.

## Verification evidence

Disposable virtual environments on runner VM169 (`.20.54`) installed
`requests==2.32.5`, `numpy==2.3.3`, `pydantic==2.11.9` and dependencies
(11 packages) with client caches disabled. Imports succeeded. Test environments
were removed after the checks; active Yesod environments were not touched.

| Check | Result |
| --- | --- |
| uv first install, mostly cold server cache | 2.831 seconds |
| uv repeat install, warm server cache | 1.464 seconds |
| pip installs after uv had warmed the cache | 12.915 and 11.191 seconds |
| Cached NumPy wheel transfer | About 113-117 MB/s as reported by pip |
| HTML and PEP 691 JSON index rewriting | Passed; artifact links point to Seykhl |
| Wheel integrity | Requests wheel SHA-256 matches index metadata |
| Cache behavior | Initial wheel MISS followed by HIT; package/metadata HITs recorded in journal |
| Service restart persistence | Requests wheel returned HIT immediately after restart, with no upstream request |
| DNS | Both `.20.202` and `.20.10` return `.20.202`; runner resolves the name |
| Host services | DNS and Proxmox proxy remained active |

These are single-run measurements, not a general speed guarantee. Pip's times
include its resolver and installation work, and both pip runs used a warm
artifact cache. A warmed server cache still needs network access from clients;
it does not turn `uv --offline` into a networked install.

[scripts/check-pypi-cache.py](scripts/check-pypi-cache.py) reproduces the
disposable pip/uv and integrity checks when deliberately run on a test client
with Python 3.13 and uv installed. It does not change system package settings.
No broad runner rollout is part of this deployment.
