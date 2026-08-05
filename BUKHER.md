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
| **Disk** | 30 GB (raw on local-lvm) |
| **Network** | vmbr0 (bridge to LAN) |
| **Net Model** | virtio |
| **Display** | none |

---

## Build Steps

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
      - FETCHER_ALLOW_PRIVATE_NETWORKS=1
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
- **Polling:** Built-in scheduler (every 30 minutes by default).

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

- Proxmox Host: `seykhl` (192.168.0.202)
- Cloud Image: `/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2`
- VM Disk: `local-lvm:vm-116-disk-0`
- Docker Compose: `/home/stephen/bukher/docker-compose.yml`
