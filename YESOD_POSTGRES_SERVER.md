# Yesod PostgreSQL production server

**Last verified:** 2026-09-05, including a recheck after the operator's
in-progress VLAN/startup repair. This audit made no changes to the running service.

## Current deployment

The server now runs as **Sefer VM 102**. The old Seykhl VM 102 is stopped
but still has autostart enabled; do not start both copies.

| Setting | Current value |
|---|---|
| Host | Sefer: VLAN `192.168.20.10`, direct 10 GbE `192.168.0.100` |
| Guest | Debian 13 (Trixie), hostname `yesod-postgres-server` |
| VM resources | 2 host vCPU / 6 GiB RAM / 120 GiB disk |
| Disk | `local:102/vm-102-disk-0.raw`, mirrored `rpool` |
| Bridge / MAC | `vmbr1` / `BC:24:11:00:88:F5` |
| Guest IPv4 | `192.168.20.155/24` (DHCP, observed after repair) |
| Tailscale IPv4 | `100.115.10.68` |
| Boot | Autostart enabled; QEMU guest agent responding |
| PostgreSQL | 17.11 (`17.11-0+deb13u1`) |
| Cluster | `17/main`, active/running, data `/var/lib/postgresql/17/main` |
| pgvector package | `postgresql-17-pgvector` 0.8.0-1 installed |

The old guest LAN address `192.168.0.155` is obsolete. The VM briefly used
`192.168.20.108` during the audit; the final observed address is `.20.155`.
The administrator Mac's `yesod-postgres-server` SSH alias still used the old
LAN address when inspected. See [NETWORK.md](NETWORK.md).

## Listeners and access rules

The final read-only query returned `listen_addresses = '*'`; `ss` showed
`0.0.0.0:5432` and `[::]:5432`. This supersedes the older Tailscale-only and
explicit-old-LAN binding descriptions.

| Endpoint | Purpose |
|---|---|
| `192.168.20.155:5432` | VLAN SQL endpoint |
| `100.115.10.68:5432` | Existing Tailscale SQL endpoint |
| Local Unix socket | Peer-authenticated administration |

The inspected `pg_hba.conf` permits password-authenticated connections using
`scram-sha-256` from localhost, `100.64.0.0/10`, `192.168.0.0/24` and
`192.168.20.0/24`. It also retains a redundant specific Tailscale-address
rule. Local socket access uses peer authentication. Replication permits local
connections and `realtime_admin` from `192.168.0.0/24`.

A matching HBA rule still requires valid role credentials and network access;
this audit did not test every application's permissions or firewall route.
Use credentials from the protected client configuration or an interactive
password prompt, not a password embedded in documentation:

```bash
psql -h 100.115.10.68 -U stephen -d stephen -W
```

## Boot ordering and September 5 repair

`postgresql@17-main.service` requests and starts after `tailscaled.service`.
Its current drop-in is:

```ini
[Unit]
Wants=tailscaled.service
After=tailscaled.service

[Service]
ExecStartPre=/usr/local/sbin/wait-for-postgresql-listen-addresses 100.115.10.68
```

The previous drop-in also waited for `192.168.0.155`, which is no longer
assigned. During the operator's repair, startup failed twice after the
90-second address wait. The live drop-in was corrected and the service started
at 17:33:11 UTC. Later checks confirmed PostgreSQL 17.11 and wildcard listeners.
No repair or restart was performed by this documentation audit.

The repository copy of the drop-in is synchronized with that observed live
configuration at [systemd/postgresql@17-main.service.d/tailscale.conf](systemd/postgresql@17-main.service.d/tailscale.conf).
The wait helper is [scripts/wait-for-postgresql-listen-addresses](scripts/wait-for-postgresql-listen-addresses).
It waits for the explicitly supplied addresses; it does not discover the SQL
listener configuration automatically.

## Databases

The read-only catalog query found 24 non-template databases. Established
application databases include `stephen`, `sjbgtd`, `sjbis`, `sjb_social`,
`clip`, `bukher`, `instasort` and `ttrac`, alongside `postgres`,
`yesod_claimdiag`, `yesod_gate` and temporary gate/recovery databases. Counts
of these temporary databases change with test activity.

The `stephen` database is the production Yesod catalog. `bukher` backs
Miniflux; `clip` and `sjb_social` support Supabase integrations. A dedicated
semantic graph reader was established in the August acceptance work; that
capability audit was not rerun here. See [YESOD_SEMANTIC_GRAPH.md](YESOD_SEMANTIC_GRAPH.md).

## Backups

The guest's current cron still runs `/home/stephen/pg_backup.sh` hourly at
`:00`. The guest timezone is UTC. The script discovers connectable databases
and dumps them using the PostgreSQL superuser (needed for complete RLS-covered
backups), plus a globals dump. Files are under `/var/backups/postgresql`.
September 5 17:00 UTC database dumps and a nonzero globals dump were present.
That is file-creation evidence, not a completed restore test.

The historical local retention is roughly six hours of hourly dumps plus
30 days of midnight dumps; the prior script record is retained below.
Current off-VM delivery is **not established**: Seykhl's hourly NAS sync still
points at `192.168.0.155`, and its monthly `vzdump 102` backs up the stopped
Seykhl copy. Sefer VM 102 is absent from both scheduled Sefer backup lists.
See [BACKUPS.md](BACKUPS.md), follow-up `proxmox-uev`.

The historic NAS paths are:

- `/mnt/proxmox-backups/yesod-postgres-server/pg_dump/`
- `/mnt/proxmox-backups/yesod-postgres-server/vzdump/`

The earlier NAS WORM configuration prevented normal deletion/rotation. Do not
claim effective retention or copy an old host cron entry unchanged to Sefer.
NAS credentials must stay in a protected credentials file, never a Markdown
mount command.

## Read-only verification

```bash
ssh -o BatchMode=yes root@sefer 'qm status 102; qm guest cmd 102 network-get-interfaces'
ssh -o BatchMode=yes root@sefer 'qm guest exec 102 -- pg_lsclusters'
ssh -o BatchMode=yes root@sefer 'qm guest exec 102 -- ss -lnt sport = :5432'
ssh -o BatchMode=yes stephen@192.168.20.155 \
  'sudo -n systemctl show postgresql@17-main -p ActiveState -p SubState -p ExecStartPre'
```

## Historical backup implementation

This retained script/restore record describes the earlier implementation. The
hourly schedule and output files were rechecked, but the entire deployed
script and restore procedure were not re-executed in this documentation audit.

### Backup Script Contents
```bash
#!/bin/bash
# PostgreSQL tiered backup
# - Hourly backups for the last 6 hours locally
# - Daily (midnight) backups for the last 30 days
# - Backs up every connectable database and PostgreSQL global objects

set -Eeuo pipefail
umask 077
BACKUP_DIR="/var/backups/postgresql"
TIMESTAMP="$(date +%Y%m%d-%H%M)"

mkdir -p "$BACKUP_DIR"

dump_stream() {
    local label="$1"
    shift
    local outfile="$BACKUP_DIR/${label}-${TIMESTAMP}.sql.gz"
    local attempt
    local errfile
    local tmpfile
    for attempt in 1 2 3; do
        tmpfile=$(mktemp "$BACKUP_DIR/.${label}-${TIMESTAMP}.XXXXXX")
        errfile="${tmpfile}.err"
        if "$@" 2>"$errfile" | gzip -c > "$tmpfile"; then
            if gzip -t "$tmpfile"; then
                mv -f "$tmpfile" "$outfile"
                chmod 600 "$outfile"
                rm -f "$errfile"
                echo "Backed up $label to $outfile ($(du -h "$outfile" | cut -f1))"
                return 0
            fi
        fi
        rm -f "$tmpfile"
        echo "WARNING: dump attempt $attempt failed for $label" >&2
        tail -c 4000 "$errfile" >&2 || true
        rm -f "$errfile"
        if (( attempt < 3 )); then sleep 10; fi
    done
    echo "ERROR: dump failed for $label after 3 attempts" >&2
    return 1
}

mapfile -t DATABASES < <(
    sudo -n -u postgres psql -XAtqc \
        "SELECT datname FROM pg_database WHERE datallowconn AND datname <> 'template0' ORDER BY datname"
)

if (( ${#DATABASES[@]} == 0 )); then
    echo "ERROR: could not find any connectable PostgreSQL databases" >&2
    exit 1
fi

for db in "${DATABASES[@]}"; do
    dump_stream "$db" sudo -n -u postgres pg_dump --format=plain --dbname="$db"
done

dump_stream globals sudo -n -u postgres pg_dumpall --globals-only

# --- Retention: keep hourly for roughly 6 hours locally, daily (midnight) for 30 days ---
find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.sql.gz" \
    -mmin +360 ! -name "*-0000.sql.gz" -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.sql.gz" -mtime +30 -delete
```

### Crontab Entry
```cron
0 * * * * /home/stephen/pg_backup.sh
```

### Restore Command
```bash
# Restore stephen database
zcat /var/backups/postgresql/stephen-20260518-1703.sql.gz | psql -U stephen -d stephen

# Restore sjb_social database
zcat /var/backups/postgresql/sjb_social-20260709-1721.sql.gz | sudo -u postgres psql -d sjb_social

# Restore bukher database
zcat /var/backups/postgresql/bukher-20260805-2311.sql.gz | sudo -u postgres psql -d bukher
```
