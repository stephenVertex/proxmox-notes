# Plan: Join yesod-postgres-server to Tailscale

## Goal
Permanently connect `yesod-postgres-server` (VMID 102, Debian 13) to your Tailscale network so it is reachable from any authenticated device on your tailnet, regardless of its LAN IP.

## Why Tailscale for This Server
- **Stable access**: DHCP IP may change; Tailscale gives a stable 100.x.x.x address
- **Secure**: No need to expose PostgreSQL or SSH to the LAN or internet
- **Convenient**: Access from any device on your tailnet (phone, laptop, other VMs)
- **Encrypted**: All traffic is WireGuard-encrypted end-to-end

## Prerequisites
- Tailscale account (with admin access to add devices)
- `yesod-postgres-server` running and reachable via SSH

## Plan

### Step 1: Install Tailscale on yesod-postgres-server

```bash
ssh stephen@yesod-postgres-server

# Debian 13 (Trixie) — add Tailscale repo and install
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt update
sudo apt install -y tailscale
```

### Step 2: Authenticate to Tailnet

**Option A: Interactive (manual, one-time)**
```bash
sudo tailscale up
# Copy the printed auth URL, open in browser, click "Authorize"
```

**Option B: Auth Key (scriptable, preferred for servers)**
1. Generate a **reusable, pre-authorized auth key** in Tailscale admin console:
   - [Tailscale Admin → Keys → Auth Keys → Generate](https://login.tailscale.com/admin/settings/keys)
   - Enable: Reusable, Ephemeral (optional), Pre-authorized
   - Set ACL tag: `tag:server` (optional but recommended)
2. On the server:
```bash
sudo tailscale up --authkey tskey-auth-xxxxxxxxxxxx
```

**Option C: OAuth (for automated provisioning)**
- Use if you plan to provision many servers automatically
- Requires OAuth client with `devices` scope

**Recommended for this server:** Option B with a pre-authorized auth key + `tag:server`

### Step 3: Verify Connection

```bash
# On yesod-postgres-server
sudo tailscale status
ip addr show tailscale0

# From any other device on your tailnet
ping <yesod-postgres-server-tailscale-ip>
ssh stephen@<yesod-postgres-server-tailscale-ip>
```

### Step 4: Make Tailscale Persistent

Tailscale service is enabled by default on install. Verify:
```bash
sudo systemctl enable tailscaled
sudo systemctl status tailscaled
```

### Step 5: Firewall / ACL Considerations

**On the server (Debian 13):**
```bash
# If ufw is active, allow Tailscale
sudo ufw allow in on tailscale0

# Or allow specific ports from tailscale0 only
sudo ufw allow in on tailscale0 to any port 5432  # PostgreSQL
sudo ufw allow in on tailscale0 to any port 22    # SSH
```

**In Tailscale ACLs (admin console):**
- If using `tag:server`, write ACL rules like:
```json
{
  "acls": [
    {"action": "accept", "src": ["group:admins"], "dst": ["tag:server:*"]}
  ],
  "tagOwners": {
    "tag:server": ["autogroup:admin"]
  }
}
```

### Step 6: Update DNS / Naming

Tailscale automatically registers the machine name. You can:
- Use MagicDNS: `yesod-postgres-server.your-tailnet.ts.net`
- Or set a custom name in the admin console

### Step 7: Update Local References

Once joined, update any local config that references `192.168.0.155` to use the Tailscale IP or MagicDNS name instead.

## Security Notes
- **Use pre-authorized auth keys** to avoid manual approval in admin console
- **Tag the device** (`tag:server`) and write restrictive ACLs
- **Do not expose PostgreSQL port 5432 on the LAN** — only via tailscale0
- **Consider disabling SSH on LAN** and only allowing it via Tailscale interface

## Verification Checklist
- [x] Tailscale installed and running
- [x] Server appears in Tailscale admin console
- [x] Can ping 100.115.10.68 from another tailnet device
- [x] Can SSH via Tailscale IP
- [x] PostgreSQL accessible via Tailscale IP:5432
- [ ] ACLs restrict access appropriately (deferred — no restrictions for now)
- [x] Server rejoins tailnet automatically after reboot

## Result
- **Tailscale IP:** 100.115.10.68
- **Tailscale Name:** yesod-postgres-server
- **Status:** Active and connected to tailnet

## PostgreSQL Tailscale Configuration

### Changes Made

**1. postgresql.conf** — Added Tailscale IP to `listen_addresses`:
```ini
listen_addresses = '100.115.10.68, localhost'
```

**2. pg_hba.conf** — Added Tailscale network access rules:
```ini
# Tailscale network access
host    all             all             100.64.0.0/10           scram-sha-256
host    all             all             100.115.10.68/32        scram-sha-256
```

### How to Connect

From any device on the tailnet:
```bash
# Using MagicDNS
psql -U stephen -d stephen -h yesod-postgres-server

# Using Tailscale IP directly
psql -U stephen -d stephen -h 100.115.10.68
```

Password: `lj*123NM`

## Alternatives Considered
- **Manual IP reservation on router**: DHCP reservation works but isn't encrypted and doesn't work across networks
- **WireGuard manual setup**: Possible but Tailscale handles key rotation, NAT traversal, and DNS automatically
- **SSH tunneling**: Works but is ad-hoc and doesn't provide stable addressing

## Resources
- [Tailscale Debian Install Docs](https://tailscale.com/kb/1039/install-debian-bookworm)
- [Tailscale Auth Keys](https://tailscale.com/kb/1085/auth-keys)
- [Tailscale ACLs](https://tailscale.com/kb/1018/acls)
- [Tailscale MagicDNS](https://tailscale.com/kb/1081/magicdns)
