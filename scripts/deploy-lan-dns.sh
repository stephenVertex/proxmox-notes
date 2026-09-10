#!/usr/bin/env bash
# Deploy the LAN DNS configuration to both fleet resolvers.
#
# The repo is the source of truth; the hosts are not. Editing
# /etc/dnsmasq.d/* or /etc/yesod/dns/infra.hosts directly on seykhl or sefer
# will be silently overwritten the next time this runs -- edit dns/ here.
#
# Deliberately driven from the workstation, which already has SSH to both
# hosts, rather than host-to-host sync. That avoids granting sefer's root an
# authorized key on seykhl purely to copy one small file.
#
# DNS ONLY. This script never deploys dns/phase2-dhcp.conf.staged. DHCP goes
# to ONE host (seykhl) by hand, after the router's VLAN 20 scope is disabled.
#
# Usage:
#   scripts/deploy-lan-dns.sh            # deploy to both, then verify
#   scripts/deploy-lan-dns.sh --check    # verify only, change nothing
#   scripts/deploy-lan-dns.sh seykhl     # deploy to one host
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DNS_DIR="$REPO_DIR/dns"

# host            address          per-host interface file
HOSTS=(
  "seykhl 192.168.20.202 11-iface-seykhl.conf"
  "sefer  192.168.20.10  11-iface-sefer.conf"
)

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new
          -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10)

# Names every resolver must be able to answer. If one of these fails the
# deploy is a failure even if dnsmasq started cleanly -- a resolver that runs
# but cannot answer is worse than one that is visibly down.
PROBES=(seykhl sefer nas router ntp dns postgres doltsvr)

say() { printf '\n=== %s\n' "$*"; }

check_host() {
  local name=$1 addr=$2 rc=0
  say "$name ($addr)"

  ssh "${SSH_OPTS[@]}" "root@$addr" '
    printf "  unit      : %s / %s / restart=%s\n" \
      "$(systemctl is-enabled dnsmasq 2>/dev/null)" \
      "$(systemctl is-active dnsmasq 2>/dev/null)" \
      "$(systemctl show dnsmasq -p Restart --value 2>/dev/null)"
    printf "  inventory : %s  (%s names)\n" \
      "$(md5sum /etc/yesod/dns/infra.hosts 2>/dev/null | cut -c1-12)" \
      "$(grep -cvE "^\s*(#|$)" /etc/yesod/dns/infra.hosts 2>/dev/null || echo 0)"
    printf "  dhcp      : %s\n" \
      "$(ss -lun 2>/dev/null | grep -q ":67 " && echo "SERVING (expected only on the phase-2 host)" || echo "not serving")"
  ' || rc=1

  local n ans
  for n in "${PROBES[@]}"; do
    ans=$(ssh "${SSH_OPTS[@]}" "root@$addr" \
            "dig +short +time=2 +tries=1 @$addr $n.internal.yesod.work A 2>/dev/null | head -1" || true)
    if [[ -z $ans ]]; then
      printf '  probe     : %-9s -> NO ANSWER\n' "$n"; rc=1
    else
      printf '  probe     : %-9s -> %s\n' "$n" "$ans"
    fi
  done

  # The zone must be local-only, and the parent domain must NOT be shadowed.
  ans=$(ssh "${SSH_OPTS[@]}" "root@$addr" \
          "dig +short +time=2 @$addr yesod.work A 2>/dev/null | head -1" || true)
  if [[ -z $ans ]]; then
    printf '  probe     : yesod.work SHADOWED -- public domain broken\n'; rc=1
  else
    printf '  probe     : yesod.work -> %s (public, correctly not shadowed)\n' "$ans"
  fi

  return $rc
}

deploy_host() {
  local name=$1 addr=$2 iface=$3
  say "deploying to $name ($addr)"

  ssh "${SSH_OPTS[@]}" "root@$addr" 'mkdir -p /etc/yesod/dns'

  scp "${SSH_OPTS[@]}" -q \
    "$DNS_DIR/infra.hosts" "root@$addr:/etc/yesod/dns/infra.hosts"
  scp "${SSH_OPTS[@]}" -q \
    "$DNS_DIR/10-yesod-lan-common.conf" "root@$addr:/etc/dnsmasq.d/10-yesod-lan-common.conf"
  scp "${SSH_OPTS[@]}" -q \
    "$DNS_DIR/$iface" "root@$addr:/etc/dnsmasq.d/11-yesod-lan-iface.conf"

  # Retire the pre-split single file if this host still has one.
  ssh "${SSH_OPTS[@]}" "root@$addr" 'rm -f /etc/dnsmasq.d/yesod-lan-dns.conf'

  # Validate BEFORE restarting. A bad config that fails --test must not take
  # the resolver down; leave the running instance alone and fail loudly.
  if ! ssh "${SSH_OPTS[@]}" "root@$addr" 'dnsmasq --test' ; then
    echo "  FAILED --test on $name; running instance left untouched" >&2
    return 1
  fi

  ssh "${SSH_OPTS[@]}" "root@$addr" 'systemctl restart dnsmasq && sleep 2 && systemctl is-active dnsmasq'
}

main() {
  local mode=${1:-all} rc=0 entry name addr iface

  if [[ $mode == --check ]]; then
    for entry in "${HOSTS[@]}"; do
      read -r name addr iface <<<"$entry"
      check_host "$name" "$addr" || rc=1
    done
    say "$([[ $rc -eq 0 ]] && echo 'ALL CHECKS PASSED' || echo 'CHECKS FAILED')"
    return $rc
  fi

  for entry in "${HOSTS[@]}"; do
    read -r name addr iface <<<"$entry"
    [[ $mode == all || $mode == "$name" ]] || continue
    deploy_host "$name" "$addr" "$iface" || rc=1
  done

  for entry in "${HOSTS[@]}"; do
    read -r name addr iface <<<"$entry"
    [[ $mode == all || $mode == "$name" ]] || continue
    check_host "$name" "$addr" || rc=1
  done

  say "$([[ $rc -eq 0 ]] && echo 'DEPLOY OK' || echo 'DEPLOY FAILED')"
  return $rc
}

main "$@"
