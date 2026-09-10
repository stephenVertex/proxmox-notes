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

# A CONSUMER on VLAN 20 that is not a gate host, used to test the path that
# actually matters. Querying a resolver directly proves only that the resolver
# answers; it does NOT prove a client is configured to ask it. That gap hid a
# real hazard on 2026-09-10: the fleet mayor found lan.planetbarr.com carries a
# public wildcard, so demons still pointed at the router were resolving service
# names to a stranger's host (103.168.172.37) while every direct query looked
# green. Resolve from the consumer, not from the resolver.
CONSUMER_HOST=sefer          # hypervisor to reach the consumer through
CONSUMER_CT=260              # idle dg4 test-db container on VLAN 20

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

# Resolve with NO explicit server, through whatever the client was actually
# given by DHCP. This is the test that counts.
check_consumer() {
  local rc=0
  say "consumer path (CT $CONSUMER_CT on $CONSUMER_HOST, no explicit server)"

  ssh "${SSH_OPTS[@]}" "root@$CONSUMER_HOST" "pct exec $CONSUMER_CT -- sh -c '
    printf \"  resolvers : %s\\n\" \"\$(awk \"/^nameserver/{printf \\\"%s \\\", \\\$2}\" /etc/resolv.conf)\"
    printf \"  search    : %s\\n\" \"\$(awk \"/^search/{print \\\$2}\" /etc/resolv.conf)\"
  '" || rc=1

  local n ans
  for n in ntp dns nas dhcp; do
    ans=$(ssh "${SSH_OPTS[@]}" "root@$CONSUMER_HOST" \
            "pct exec $CONSUMER_CT -- getent ahostsv4 $n.internal.yesod.work 2>/dev/null | head -1 | awk '{print \$1}'" || true)
    if [[ -z $ans ]]; then
      printf '  fqdn      : %-5s -> NOT FOUND (consumer cannot reach the resolver)\n' "$n"; rc=1
    else
      printf '  fqdn      : %-5s -> %s\n' "$n" "$ans"
    fi
  done

  # The retired wildcarded zone must fail closed, never return an address.
  ans=$(ssh "${SSH_OPTS[@]}" "root@$CONSUMER_HOST" \
          "pct exec $CONSUMER_CT -- getent ahostsv4 ntp.lan.planetbarr.com 2>/dev/null | head -1 | awk '{print \$1}'" || true)
  if [[ -n $ans ]]; then
    printf '  wildcard  : ntp.lan.planetbarr.com -> %s  ** LEAKING TO A STRANGER **\n' "$ans"; rc=1
  else
    printf '  wildcard  : ntp.lan.planetbarr.com -> correctly fails closed\n'
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
    check_consumer || rc=1
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
  [[ $mode == all ]] && { check_consumer || rc=1; }

  say "$([[ $rc -eq 0 ]] && echo 'DEPLOY OK' || echo 'DEPLOY FAILED')"
  return $rc
}

main "$@"
