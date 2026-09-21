#!/usr/bin/env bash
# Deploy only the cache service. DNS inventory deployment is separate.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
target=${1:-root@seykhl}
stage=$(ssh -o BatchMode=yes "$target" 'mktemp -d /tmp/pypi-cache-deploy.XXXXXXXX')
scp -o BatchMode=yes "$repo_dir/pypi-cache/nginx.conf" \
    "$repo_dir/systemd/pypi-cache.service" "$target:$stage/"
ssh -o BatchMode=yes "$target" bash -s -- "$stage" <<'REMOTE'
set -euo pipefail
stage=$1
test "$(id -u)" = 0
ip -4 addr show | grep -q 'inet 192.168.20.202/'
# Avoid starting the package's default web server on a Proxmox host.
if systemctl is-active --quiet nginx.service; then
    echo 'An existing nginx.service is active; refusing to replace it.' >&2
    exit 1
fi
systemctl mask nginx.service
if ! command -v nginx >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nginx
fi
backup=$(mktemp -d /etc/pypi-cache-before.XXXXXXXX)
for file in /etc/pypi-cache/nginx.conf /etc/systemd/system/pypi-cache.service; do
    if test -f "$file"; then cp -f "$file" "$backup/"; fi
done
was_active=false
if systemctl is-active --quiet pypi-cache.service; then was_active=true; fi
rollback() {
    echo "Deployment failed; restoring configuration from $backup" >&2
    if test -f "$backup/nginx.conf"; then
        install -m 0644 "$backup/nginx.conf" /etc/pypi-cache/nginx.conf
        install -m 0644 "$backup/pypi-cache.service" /etc/systemd/system/pypi-cache.service
        systemctl daemon-reload
        if "$was_active"; then systemctl restart pypi-cache.service; fi
    else
        systemctl disable --now pypi-cache.service || true
    fi
}
trap rollback ERR
install -d -m 0755 /etc/pypi-cache
install -m 0644 "$stage/nginx.conf" /etc/pypi-cache/nginx.conf
install -m 0644 "$stage/pypi-cache.service" /etc/systemd/system/pypi-cache.service
systemd-analyze verify /etc/systemd/system/pypi-cache.service
systemctl daemon-reload
systemctl enable pypi-cache.service
systemctl restart pypi-cache.service
# ExecStartPre validates nginx inside the same unprivileged service sandbox.
for attempt in {1..20}; do
    if curl --max-time 5 -fsS http://127.0.0.1:3141/healthz; then break; fi
    sleep 1
done
curl --max-time 5 -fsS http://127.0.0.1:3141/healthz
systemctl is-active pypi-cache.service
trap - ERR
echo "Configuration backup: $backup"
REMOTE
