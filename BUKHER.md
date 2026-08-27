# Bukher — RSS Ingestion Node

## Overview

**Bukher** is a Proxmox VM that runs **RssHub** + **Miniflux** to ingest RSS feeds (starting with Twitter/X feeds) and store them in a dedicated PostgreSQL database on `yesod-postgres-server`.

- **RssHub** generates RSS feeds from sources that don't provide them natively (e.g., Twitter/X).
- **Miniflux** polls, stores, and serves the RSS entries.

---

## VM Specifications

| Setting | Value |
|---------|-------|
| **VMID** | 116 |
| **Name** | bukher |
| **OS** | Debian 13 "Trixie" |
| **CPU** | host |
| **Cores** | 2 |
| **Memory** | 4 GB |
| **Disk** | 30 GB on `vmdata` |
| **Network** | vmbr0 (bridge to LAN) |
| **Net Model** | virtio |
| **Display** | none |

---

## Build Steps

> **Historical provisioning record:** these steps were performed on the
> retired `seykhl` host and deliberately retain its original storage commands.
> The current VM configuration is recorded in [Current host and backup status](#current-host-and-backup-status).

### 1. Create VM on Proxmox

```bash
# On seykhl (Proxmox host)
ssh root@seykhl

qm create 116 \
  --name bukher \
  --memory 4096 \
  --cores 2 \
  --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-single \
  --boot order=scsi0 \
  --ostype l26 \
  --agent enabled=1

qm disk import 116 /var/lib/vz/template/iso/debian-13-generic-amd64.qcow2 local-lvm
qm set 116 --scsi0 local-lvm:vm-116-disk-0
qm disk resize 116 scsi0 30G
qm set 116 --ide2 local-lvm:cloudinit
qm set 116 --ciuser stephen
qm set 116 --cipassword '<hidden>'
qm set 116 --ipconfig0 ip=dhcp
qm start 116
```

### 2. Inject SSH Key (Password Auth Disabled)

See [`SSH_ENABLE_HOWTO.md`](./SSH_ENABLE_HOWTO.md) for the offline disk-mount method. After key injection:

```bash
ssh stephen@192.168.0.169
```

### 3. Post-Install Setup

```bash
sudo hostnamectl set-hostname bukher
sudo apt update
sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker stephen

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sudo sh
sudo tailscale up

# Install avahi-daemon for mDNS
sudo apt install -y avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon

# Configure avahi to advertise only on eth0
sudo sed -i 's/^#allow-interfaces=.*/allow-interfaces=eth0/' /etc/avahi/avahi-daemon.conf
sudo systemctl restart avahi-daemon
```

---

## Network Details

| Interface | Value |
|-----------|-------|
| **MAC Address** | BC:24:11:51:5F:AD |
| **LAN IP** | 192.168.0.169 (DHCP) |
| **mDNS Name** | `bukher.local` |
| **Tailscale IP** | 100.77.145.88 |
| **Tailscale Name** | `bukher` |

---

## Tailscale Access

- **Status:** Connected to tailnet `tailb4b58.ts.net`
- **MagicDNS:** `bukher.tailb4b58.ts.net`
- **CLI check:** `tailscale status` on any tailnet node shows `100.77.145.88 bukher ... linux -`

## Current host and backup status

- **Proxmox host:** `sefer` (`192.168.0.100`)
- **VM disk:** `vmdata:vm-116-disk-0`
- **VM backup:** included in the nightly 03:30 `sefer-light-services` snapshot
  job on `nas-backups` (7 daily, 4 weekly, 3 monthly retained)
- **Guest agent:** configured in the VM but not responding during the
  2026-08-27 inventory; use SSH or console access until it is repaired.

---

## Services

### Docker Compose Stack

Location: `/home/stephen/bukher/docker-compose.yml`

```yaml
services:
  rsshub:
    image: diygod/rsshub:latest
    container_name: rsshub
    restart: unless-stopped
    ports:
      - "100.77.145.88:1200:1200"
    environment:
      - NODE_ENV=production
      - CACHE_TYPE=memory
      - TWITTER_AUTH_TOKEN=<your-auth-token>
    networks:
      - bukher-net

  miniflux:
    image: miniflux/miniflux:latest
    container_name: miniflux
    restart: unless-stopped
    ports:
      - "100.77.145.88:8080:8080"
    environment:
      - DATABASE_URL=postgres://bukher:bukher2026@100.115.10.68:5432/bukher?sslmode=disable
      - RUN_MIGRATIONS=1
      - CREATE_ADMIN=0
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=h14K1SClFMz6Q17TStiOv9KTfWVUQZtv
      - BASE_URL=https://bukher.tailb4b58.ts.net
      - POLLING_FREQUENCY=30
      - DISABLE_SCHEDULER_SERVICE=1
      - FETCHER_ALLOW_PRIVATE_NETWORKS=1
      - HTTP_CLIENT_TIMEOUT=45
    networks:
      - bukher-net
    depends_on:
      - rsshub

networks:
  bukher-net:
    driver: bridge
```

### RssHub

- **URL:** `http://bukher.tailb4b58.ts.net:1200` or `http://100.77.145.88:1200`
- **Purpose:** Generate RSS feeds for sources without native RSS (e.g., Twitter/X).

### Miniflux

- **URL:** `http://bukher.tailb4b58.ts.net:8080` or `http://100.77.145.88:8080`
- **Admin Username:** `admin`
- **Admin Password:** `h14K1SClFMz6Q17TStiOv9KTfWVUQZtv`
- **Purpose:** Poll RSS feeds, store entries, and provide a web UI/API.
- **Polling:** Miniflux's built-in batch scheduler is disabled (`DISABLE_SCHEDULER_SERVICE=1`). Feeds are instead
  refreshed individually on a staggered schedule — see [Staggered Feed Refresh](#staggered-feed-refresh) below.

### Management

```bash
# Start / stop / restart
cd ~/bukher
sudo docker compose up -d
sudo docker compose down
sudo docker compose restart

# View logs
sudo docker compose logs -f
sudo docker compose logs -f miniflux
sudo docker compose logs -f rsshub
```

### Staggered Feed Refresh

With 100+ tracked feeds, Miniflux's built-in batch poller was hitting all feeds in the same
window, overwhelming RssHub and causing widespread `context deadline exceeded` errors. Fixed
(2026-08-06) by disabling the batch scheduler and refreshing feeds individually, spread across
a 4-hour cycle based on the first letter of the Twitter handle.

- **Script:** `/home/stephen/bukher/stagger_refresh.py`
- **Trigger:** systemd timer `bukher-feed-stagger.timer`, runs every 5 minutes
- **Logic:** 27 buckets (`a`-`z` + `_` for non-alphabetic handles) spaced ~8.9 min apart across
  a 240-minute (4h) cycle. Each run checks which bucket(s) are due and calls
  `PUT /v1/feeds/{id}/refresh` for just those feeds — so each feed gets refreshed roughly every
  4 hours, and only a handful of feeds are ever in flight at once.
- **Timeout:** `HTTP_CLIENT_TIMEOUT=45` (up from Miniflux's 20s default) gives slow
  Twitter/RssHub scrapes more room; occasional individual timeouts self-correct on the next
  ~4-hour pass since they don't block other feeds.

**`/home/stephen/bukher/stagger_refresh.py`:**

```python
#!/usr/bin/env python3
"""Refresh Miniflux feeds on a letter-staggered ~4h cycle instead of one big batch poll."""
import string
import sys
import time

import requests

MINIFLUX_URL = "http://100.77.145.88:8080"
AUTH = ("admin", "h14K1SClFMz6Q17TStiOv9KTfWVUQZtv")
CYCLE_MINUTES = 240  # 4 hours
BUCKET_KEYS = list(string.ascii_lowercase) + ["_"]  # 27 buckets; non a-z first chars fold into "_"
SLOT_SPACING = CYCLE_MINUTES / len(BUCKET_KEYS)  # ~8.89 min apart
WINDOW_MINUTES = 5  # must match the systemd timer's run interval


def bucket_for_handle(handle):
    c = handle[0].lower()
    return c if c in string.ascii_lowercase else "_"


def slot_minute(bucket_key):
    idx = BUCKET_KEYS.index(bucket_key)
    return idx * SLOT_SPACING


def due_buckets(now_minute):
    due = set()
    for key in BUCKET_KEYS:
        slot = slot_minute(key)
        delta = (now_minute - slot) % CYCLE_MINUTES
        if delta < WINDOW_MINUTES:
            due.add(key)
    return due


def main():
    now_minute = (time.time() / 60) % CYCLE_MINUTES
    due = due_buckets(now_minute)
    if not due:
        return

    resp = requests.get(f"{MINIFLUX_URL}/v1/feeds", auth=AUTH, timeout=30)
    resp.raise_for_status()
    feeds = resp.json()

    to_refresh = [f for f in feeds if bucket_for_handle(f["feed_url"].rsplit("/", 1)[-1]) in due]
    if not to_refresh:
        print(f"buckets due={sorted(due)} but no matching feeds")
        return

    print(f"buckets due={sorted(due)} refreshing {len(to_refresh)} feed(s)")
    for feed in to_refresh:
        handle = feed["feed_url"].rsplit("/", 1)[-1]
        try:
            r = requests.put(f"{MINIFLUX_URL}/v1/feeds/{feed['id']}/refresh", auth=AUTH, timeout=60)
            print(f"  {handle}: HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  {handle}: ERROR {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

**`/etc/systemd/system/bukher-feed-stagger.service`:**

```ini
[Unit]
Description=Bukher staggered Miniflux feed refresh

[Service]
Type=oneshot
User=stephen
ExecStart=/usr/bin/python3 /home/stephen/bukher/stagger_refresh.py
```

**`/etc/systemd/system/bukher-feed-stagger.timer`:**

```ini
[Unit]
Description=Run bukher-feed-stagger every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
AccuracySec=10s

[Install]
WantedBy=timers.target
```

```bash
# Check timer status / logs
systemctl status bukher-feed-stagger.timer
sudo journalctl -u bukher-feed-stagger.service -n 50 --no-pager

# Run a refresh cycle manually
sudo systemctl start bukher-feed-stagger.service
```

---

## Database

Bukher uses a dedicated PostgreSQL database on `yesod-postgres-server`.

| Parameter | Value |
|-----------|-------|
| **Host** | `yesod-postgres-server` (MagicDNS) or `100.115.10.68` |
| **Port** | `5432` |
| **Database** | `bukher` |
| **Username** | `bukher` |
| **Password** | `bukher2026` |
| **SSL** | `disable` (Tailscale encrypts the tunnel) |

### Connection String

```
postgres://bukher:bukher2026@100.115.10.68:5432/bukher?sslmode=disable
```

### Backup

The bukher database is included in the hourly tiered backup on `yesod-postgres-server`:

- **Script:** `/home/stephen/pg_backup.sh`
- **Backup file:** `/var/backups/postgresql/bukher-YYYYMMDD-HHMM.sql.gz`
- **Daily midnight backups** are synced to the NAS under `/mnt/proxmox-backups/yesod-postgres-server/pg_dump/`.

---

## Twitter Feeds

Feeds are configured in Miniflux. RssHub provides Twitter/X routes such as:

- `/twitter/user/{handle}` — tweets from a user
- `/twitter/user/{handle}/exclude_replies` — tweets excluding replies

### Authentication

Twitter/X now blocks unauthenticated scraping. RssHub is configured with `TWITTER_AUTH_TOKEN` set to a logged-in X web session's `auth_token` cookie. If feeds stop working, extract a fresh `auth_token` from a Chrome session (Application → Cookies → https://x.com → `auth_token`) and update the environment variable in `docker-compose.yml`, then restart RssHub.

### Current Feeds (53 accounts)

All feeds are in the **X/Twitter** category and are polled automatically by Miniflux.

| Handle | RssHub Feed URL |
|--------|-----------------|
| MerrittBaer | `http://bukher.tailb4b58.ts.net:1200/twitter/user/MerrittBaer` |
| Prince_Canuma | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Prince_Canuma` |
| measure_plan | `http://bukher.tailb4b58.ts.net:1200/twitter/user/measure_plan` |
| SkylerMiao7 | `http://bukher.tailb4b58.ts.net:1200/twitter/user/SkylerMiao7` |
| steipete | `http://bukher.tailb4b58.ts.net:1200/twitter/user/steipete` |
| theo | `http://bukher.tailb4b58.ts.net:1200/twitter/user/theo` |
| jeffscottward | `http://bukher.tailb4b58.ts.net:1200/twitter/user/jeffscottward` |
| claudeai | `http://bukher.tailb4b58.ts.net:1200/twitter/user/claudeai` |
| TheAhmadOsman | `http://bukher.tailb4b58.ts.net:1200/twitter/user/TheAhmadOsman` |
| Josikinz | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Josikinz` |
| olidinov | `http://bukher.tailb4b58.ts.net:1200/twitter/user/olidinov` |
| kevinlu625 | `http://bukher.tailb4b58.ts.net:1200/twitter/user/kevinlu625` |
| chetaslua | `http://bukher.tailb4b58.ts.net:1200/twitter/user/chetaslua` |
| AIconference | `http://bukher.tailb4b58.ts.net:1200/twitter/user/AIconference` |
| samruddhi_mokal | `http://bukher.tailb4b58.ts.net:1200/twitter/user/samruddhi_mokal` |
| grok | `http://bukher.tailb4b58.ts.net:1200/twitter/user/grok` |
| PrajwalTomar_ | `http://bukher.tailb4b58.ts.net:1200/twitter/user/PrajwalTomar_` |
| mikefutia | `http://bukher.tailb4b58.ts.net:1200/twitter/user/mikefutia` |
| Yampeleg | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Yampeleg` |
| thursdai_pod | `http://bukher.tailb4b58.ts.net:1200/twitter/user/thursdai_pod` |
| altryne | `http://bukher.tailb4b58.ts.net:1200/twitter/user/altryne` |
| WolframRvnwlf | `http://bukher.tailb4b58.ts.net:1200/twitter/user/WolframRvnwlf` |
| raycast | `http://bukher.tailb4b58.ts.net:1200/twitter/user/raycast` |
| MskabaCyborg | `http://bukher.tailb4b58.ts.net:1200/twitter/user/MskabaCyborg` |
| colin_fraser | `http://bukher.tailb4b58.ts.net:1200/twitter/user/colin_fraser` |
| cline | `http://bukher.tailb4b58.ts.net:1200/twitter/user/cline` |
| dannyveigatx | `http://bukher.tailb4b58.ts.net:1200/twitter/user/dannyveigatx` |
| Kling_ai | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Kling_ai` |
| arpangup | `http://bukher.tailb4b58.ts.net:1200/twitter/user/arpangup` |
| ephor | `http://bukher.tailb4b58.ts.net:1200/twitter/user/ephor` |
| OpsAIGuru | `http://bukher.tailb4b58.ts.net:1200/twitter/user/OpsAIGuru` |
| AiAutodidact | `http://bukher.tailb4b58.ts.net:1200/twitter/user/AiAutodidact` |
| batsirai | `http://bukher.tailb4b58.ts.net:1200/twitter/user/batsirai` |
| Longevity_EDU | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Longevity_EDU` |
| ErikSchluntz | `http://bukher.tailb4b58.ts.net:1200/twitter/user/ErikSchluntz` |
| AravSrinivas | `http://bukher.tailb4b58.ts.net:1200/twitter/user/AravSrinivas` |
| kevinkern | `http://bukher.tailb4b58.ts.net:1200/twitter/user/kevinkern` |
| seobotai | `http://bukher.tailb4b58.ts.net:1200/twitter/user/seobotai` |
| illyism | `http://bukher.tailb4b58.ts.net:1200/twitter/user/illyism` |
| techwithmatheus | `http://bukher.tailb4b58.ts.net:1200/twitter/user/techwithmatheus` |
| screenpipe | `http://bukher.tailb4b58.ts.net:1200/twitter/user/screenpipe` |
| svpino | `http://bukher.tailb4b58.ts.net:1200/twitter/user/svpino` |
| tqbf | `http://bukher.tailb4b58.ts.net:1200/twitter/user/tqbf` |
| Crossover4Work | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Crossover4Work` |
| AnjneyMidha | `http://bukher.tailb4b58.ts.net:1200/twitter/user/AnjneyMidha` |
| cursor_ai | `http://bukher.tailb4b58.ts.net:1200/twitter/user/cursor_ai` |
| _rk_singhal | `http://bukher.tailb4b58.ts.net:1200/twitter/user/_rk_singhal` |
| aiDotEngineer | `http://bukher.tailb4b58.ts.net:1200/twitter/user/aiDotEngineer` |
| supabase | `http://bukher.tailb4b58.ts.net:1200/twitter/user/supabase` |
| artificialguybr | `http://bukher.tailb4b58.ts.net:1200/twitter/user/artificialguybr` |
| Lovable | `http://bukher.tailb4b58.ts.net:1200/twitter/user/Lovable` |
| 3blue1brown | `http://bukher.tailb4b58.ts.net:1200/twitter/user/3blue1brown` |
| maishsk | `http://bukher.tailb4b58.ts.net:1200/twitter/user/maishsk` |

> **Note:** Twitter/X rate limits and anti-bot checks can still cause intermittent failures even with a valid `auth_token`. If a feed stops updating, refresh the token or add a secondary comma-separated token to `TWITTER_AUTH_TOKEN`.

---

## Security Notes

- **Tailscale only:** RssHub and Miniflux ports are bound to the Tailscale IP (`100.77.145.88`), so they are not reachable via the LAN or public internet.
- **SSH:** Password authentication was disabled by the cloud image. Access is via SSH key only.
- **Database:** PostgreSQL is accessed over Tailscale with SSL disabled; Tailscale provides the encryption layer.

---

## Resources

- Proxmox Host: `sefer` (192.168.0.100)
- Cloud Image: `/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2`
- VM Disk: `vmdata:vm-116-disk-0`
- Docker Compose: `/home/stephen/bukher/docker-compose.yml`
