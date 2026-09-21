#!/usr/bin/env bash
# Add the PyPI alias without restarting dnsmasq or touching DHCP configuration.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
inventory="$repo_dir/dns/infra.hosts"
old_hash=$(sed '/^192\.168\.20\.202  pypi\.internal\.yesod\.work pypi\.lan pypi$/d' "$inventory" | shasum -a 256 | awk '{print $1}')
new_hash=$(shasum -a 256 "$inventory" | awk '{print $1}')
for target in root@seykhl root@sefer; do
    stage=$(ssh -o BatchMode=yes "$target" 'mktemp /tmp/pypi-dns.XXXXXXXX')
    scp -o BatchMode=yes "$inventory" "$target:$stage"
    ssh -o BatchMode=yes "$target" bash -s -- "$stage" "$old_hash" "$new_hash" <<'REMOTE'
set -euo pipefail
stage=$1
old_hash=$2
new_hash=$3
inventory=/etc/yesod/dns/infra.hosts
current_hash=$(sha256sum "$inventory" | awk '{print $1}')
test "$(sha256sum "$stage" | awk '{print $1}')" = "$new_hash"
if test "$current_hash" = "$new_hash"; then
    echo 'PyPI DNS alias is already deployed.'
    exit 0
fi
if test "$current_hash" != "$old_hash"; then
    echo 'DNS inventory has drifted; reconcile it with the repository first.' >&2
    exit 1
fi
dnsmasq --test
backup=$(mktemp /etc/yesod/dns/infra.hosts.before-pypi.XXXXXXXX)
cp -f "$inventory" "$backup"
install -m 0644 "$stage" "$inventory.new"
mv -f "$inventory.new" "$inventory"
systemctl reload dnsmasq
systemctl is-active dnsmasq
echo "DNS inventory backup: $backup"
REMOTE
done
