# Supabase Edge Runtime Node — sb-edge

**Provisioned:** 2026-06-12  
**Purpose:** Isolated Supabase Edge Runtime host for sjbgtd Supabase→seykhl migration. Runs [supabase/edge-runtime](https://github.com/supabase/edge-runtime) — a Deno-based server for TypeScript edge functions that mirrors the Supabase hosted edge function API.

---

## VM Specs

| Field | Value |
|-------|-------|
| **Proxmox VM ID** | 111 |
| **VM Name** | sb-edge |
| **Host** | seykhl (192.168.0.202) |
| **IP** | 192.168.0.137 (static, set in guest) |
| **MAC** | BC:24:11:5E:D5:A8 |
| **OS** | Debian GNU/Linux 13 (trixie) |
| **CPU** | 2 cores |
| **RAM** | 4 GB |
| **Disk** | 20 GB (lvmthin on local-lvm) |
| **SSH user** | stephen |
| **Cloned from** | VM 109 (yesod-runner-base) |

> **VM vs LXC decision:** Docker inside LXC requires a privileged container; the edge-runtime binary approach avoids Docker entirely. VM chosen to follow the established house pattern (clone from VM 109), avoid privileged LXC footprint, and ensure clean isolation.

> **Router DHCP reservation:** A reservation for MAC `BC:24:11:5E:D5:A8` → `192.168.0.137` is recommended as belt-and-suspenders insurance. The VM has a static IP set inside the guest (not DHCP-dependent), but a router reservation prevents .137 from being handed to another device.

---

## SSH Access

```bash
ssh stephen@sb-edge          # alias in ~/.ssh/config on sjbmbp
ssh stephen@192.168.0.137    # direct IP
```

Add to sjbmbp `/etc/hosts` if not already present:
```bash
sudo bash -c 'echo "192.168.0.137 sb-edge" >> /etc/hosts'
```

---

## Edge Runtime Installation

**Binary:** supabase/edge-runtime v1.74.1 (Deno 2.1.4), installed to `/opt/edge-runtime/`.

```
/opt/edge-runtime/
  bin/
    edge-runtime          # wrapper shell script (sets LD_LIBRARY_PATH)
    .edge-runtime-wrapped # actual 160MB binary
  lib/
    libabsl_*.so.*        # bundled shared libraries
    ...
```

`/usr/local/bin/edge-runtime` is a thin wrapper that calls `/opt/edge-runtime/bin/edge-runtime`.

**To update the runtime:**
```bash
# On sb-edge
VER=v1.xx.x
curl -fsSL https://github.com/supabase/edge-runtime/releases/download/$VER/edge-runtime-$VER-x86_64-linux.tar.gz -o /tmp/er.tar.gz
tar xzf /tmp/er.tar.gz -C /tmp/edge-runtime-new
sudo systemctl stop supabase-edge-runtime
sudo cp -r /tmp/edge-runtime-new/bin /opt/edge-runtime/
sudo cp -r /tmp/edge-runtime-new/lib /opt/edge-runtime/
sudo systemctl start supabase-edge-runtime
```

---

## Functions Directory

```
/home/stephen/functions/
  main/
    index.ts    # main service — routes /functions/v1/<name> to user workers
  hello/
    index.ts    # hello-world verification function
  <your-function>/
    index.ts    # add new functions here
```

### Main service (`functions/main/index.ts`)

Routes requests matching `/functions/v1/<function-name>` to user workers in `/home/stephen/functions/<function-name>/`. Serves `/health` → `ok`.

### Adding a new function

```bash
mkdir -p ~/functions/my-function
cat > ~/functions/my-function/index.ts << 'EOF'
Deno.serve((_req: Request) => {
  return new Response(JSON.stringify({ result: "hello from my-function" }), {
    headers: { "Content-Type": "application/json" },
  })
})
EOF
# No restart needed — workers are created on first request
curl http://sb-edge:9000/functions/v1/my-function
```

---

## Systemd Service

**Unit file:** `/etc/systemd/system/supabase-edge-runtime.service`

```ini
[Unit]
Description=Supabase Edge Runtime
After=network-online.target
Wants=network-online.target

[Service]
User=stephen
Group=stephen
Type=simple
ExecStart=/opt/edge-runtime/bin/edge-runtime start \
  --main-service /home/stephen/functions/main \
  --port 9000 \
  --ip 0.0.0.0
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/supabase-edge-runtime.log
StandardError=append:/var/log/supabase-edge-runtime.log

[Install]
WantedBy=multi-user.target
```

**Service commands:**
```bash
sudo systemctl status supabase-edge-runtime
sudo systemctl restart supabase-edge-runtime
sudo systemctl stop supabase-edge-runtime
sudo tail -f /var/log/supabase-edge-runtime.log
```

**Enabled:** yes (`systemctl enable`) — starts automatically on boot.

---

## Verification

```bash
# Health check
curl http://sb-edge:9000/health
# → ok

# Hello-world function
curl http://sb-edge:9000/functions/v1/hello
# → {"hello":"world","runtime":"supabase-edge-runtime","host":"localhost"}

# Or via IP (no /etc/hosts needed)
curl http://192.168.0.137:9000/functions/v1/hello
```

**Confirmed working** on 2026-06-12 — both health and hello function return correct responses from sjbmbp.

---

## Network Config on sb-edge

Static IP is set via systemd-networkd (cloud-init network management disabled):

```
/etc/systemd/network/10-eth0.network
/etc/cloud/cloud.cfg.d/99-disable-network.cfg  ← prevents cloud-init from overriding static IP on reboot
```

---

## Next Steps (sjbgtd Migration Epic)

- **pgvector** needs to be installed on `yesod-postgres-server` before the sjbgtd DB migration can proceed: `sudo apt install postgresql-17-pgvector` on VM 102.
- The sjbgtd migration epic (`task #12`) will deploy real edge functions to `~/functions/` on sb-edge, replacing the hello-world placeholder.
- Consider adding `sb-edge` to the yesod infra monitoring sweep once real functions are deployed.
