# Domain Registry

**Last updated:** 2026-07-22

---

## meshcrawler.com

| Field | Value |
|-------|-------|
| **Registrar** | Namecheap |
| **DNS** | Cloudflare (`adaline.ns.cloudflare.com`, `jimmy.ns.cloudflare.com`) |
| **Cloudflare Zone ID** | `3ea596f72ef21f4cbf67efaf2456fca2` |
| **Plan** | Cloudflare Pro |
| **Previous DNS** | Route 53 (migrated back to Cloudflare 2026-07-22) |
| **Route 53 Zone IDs** | `Z0810906C526BUOORYFC` (delegated, now stale), `Z0356075ECD65FKGTUF0` (not delegated) |

### Email

| Field | Value |
|-------|-------|
| **Provider** | Fastmail |
| **MX** | `10 in1-smtp.messagingengine.com`, `20 in2-smtp.messagingengine.com` |
| **SPF** | `v=spf1 include:spf.messagingengine.com ?all` |
| **DMARC** | `v=DMARC1; p=none;` |
| **DKIM** | `fm1._domainkey` → `fm1.meshcrawler.com.dkim.fmhosted.com` |
| | `fm2._domainkey` → `fm2.meshcrawler.com.dkim.fmhosted.com` |
| | `fm3._domainkey` → `fm3.meshcrawler.com.dkim.fmhosted.com` |
| **SRV** | Fastmail autodiscover, caldav, carddav, imap, pop3, smtp |

### Subdomains & Services

| Subdomain | Type | Target | Proxied | Service |
|-----------|------|--------|---------|---------|
| `meshcrawler.com` (apex) | A | `103.168.172.52`, `103.168.172.37` | Yes | CloudFront site |
| `www` | A | `103.168.172.37`, `103.168.172.52` | Yes | CloudFront site |
| `n8n` | CNAME | `6b2b99a2-4fb1-4e88-be58-fca8b9d6fd2e.cfargotunnel.com` | Yes | n8n automation (VM 107, `n8n-server`, 192.168.0.145) |
| `docuseal` | CNAME | `fdbd66cf-8ea3-4f25-8ea8-440997b14378.cfargotunnel.com` | Yes | DocuSeal document signing (VM 113, `docuseal`, 192.168.0.139) |
| `mail` | A | `103.168.172.65` | Yes | Fastmail mail server |
| `*.meshcrawler.com` | A | `103.168.172.52`, `103.168.172.37` | Yes | Wildcard catch-all |

### Cloudflare Tunnels

| Tunnel | ID | VM | Config |
|--------|----|----|--------|
| n8n | `6b2b99a2-4fb1-4e88-be58-fca8b9d6fd2e` | 107 (n8n-server) | `/etc/cloudflared/config.yml` → `localhost:5678` |
| docuseal | `fdbd66cf-8ea3-4f25-8ea8-440997b14378` | 113 (docuseal) | `/etc/cloudflared/config.yml` → `localhost:3000` |

### Notes
- Migrated DNS from Namecheap → Route 53 → Cloudflare (back) on 2026-07-22
- Route 53 zone `Z0810906C526BUOORYFC` was the active delegated zone before migration
- Cloudflare Tunnels require Cloudflare DNS for `cfargotunnel.com` CNAMEs to resolve — does not work with Route 53
- The `_2264e785400799a90f3c2bef22202402` CNAME is an ACM validation record

---

## aicoe.fit

| Field | Value |
|-------|-------|
| **Registrar** | Namecheap |
| **DNS** | Cloudflare (`adaline.ns.cloudflare.com`, `jimmy.ns.cloudflare.com`) |
| **Cloudflare Zone ID** | `9ebfb9032a1a6387c1940d2d327bcb9a` |
| **Plan** | Cloudflare Free |
| **Original NS** | `dns1.registrar-servers.com`, `dns2.registrar-servers.com` (Namecheap) |

### Subdomains & Services

| Subdomain | Type | Target | Service |
|-----------|------|--------|---------|
| _(add as needed)_ | | | |

### Notes
- Cloudflare API token has limited permissions on this zone (worker + R2 only, no DNS edit)
- Stray CNAME `docuseal.meshcrawler.com.aicoe.fit` was accidentally created by `cloudflared tunnel route dns` — needs cleanup in Cloudflare dashboard

---

## tailb4b58.ts.net

| Field | Value |
|-------|-------|
| **Registrar** | Tailscale (managed) |
| **DNS** | Tailscale MagicDNS |
| **Type** | Tailnet domain (not a public domain) |

### Tailscale Nodes

| Hostname | Tailscale IP | VMID | OS |
|----------|-------------|------|----|
| docuseal | 100.117.77.67 | 113 | Debian 13 |
| dertog | 100.64.95.60 | 104 | Debian 13 |
| doltsvr | 100.101.145.38 | 100 | Debian 13 |
| sb-edge | 100.115.156.68 | 111 | Debian 13 |
| yesod-dispatch | 100.123.34.77 | 112 | Debian 13 |
| yesod-postgres-server | 100.115.10.68 | 102 | Debian 13 |
| homestar | 100.120.51.13 | — | Synology NAS |
| strongsad | 100.120.185.140 | — | Linux |
| pompom | 100.83.178.107 | — | macOS |
| stephens-macbook-air-3 | 100.123.203.70 | — | macOS |
| stephens-macbook-pro-1 | 100.110.179.106 | — | macOS |
| iphone182 | 100.127.208.109 | — | iOS |

### Tailscale HTTPS Endpoints

| URL | Service |
|-----|---------|
| `https://docuseal.tailb4b58.ts.net/` | DocuSeal (via `tailscale serve`) |
| `https://sb-edge.tailb4b58.ts.net/rest/v1/` | PostgREST API |
| `https://sb-edge.tailb4b58.ts.net/functions/v1/` | Supabase Edge Functions |

### Notes
- Tailscale MagicDNS provides `*.tailb4b58.ts.net` hostnames for all tailnet nodes
- `tailscale serve` provides HTTPS within the tailnet (not public)
- `tailscale funnel` can expose services publicly (not currently configured)
