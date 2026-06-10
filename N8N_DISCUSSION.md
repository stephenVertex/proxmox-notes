# N8N Discussion & Setup Notes

## Date: 2026-06-10
## Context: n8n Server Setup on Proxmox

---

## What is n8n?

n8n is an open-source workflow automation platform. It provides a visual editor for building automated workflows by connecting nodes that represent different services, APIs, and operations.

## Architecture Overview

**n8n Server Setup (VMID 107):**
- **VM:** n8n-server (192.168.0.145)
- **OS:** Debian 12
- **Install Method:** npm (not Docker)
- **Port:** 5678 (localhost only)
- **Reverse Proxy:** Cloudflare Tunnel
- **Public URL:** https://n8n.meshcrawler.com
- **TLS:** Valid certificate via Cloudflare (Google Trust Services)

**Why VM + npm (not Docker):**
- User wanted simplicity and minimal layers of indirection
- Proxmox provides isolation at the VM level
- Direct npm install is straightforward for a single-purpose VM

## Services on the VM

1. **n8n** (systemd service)
   - Binds to localhost:5678
   - Auto-starts on boot
   - Basic auth: admin/admin
   - Database: SQLite
   - Logs: `sudo journalctl -u n8n -f`

2. **cloudflared** (Cloudflare Tunnel)
   - Exposes n8n to the internet via tunnel
   - No port forwarding needed
   - Config: `/etc/cloudflared/config.yml`
   - Logs: `sudo journalctl -u cloudflared -f`

3. **Caddy** (optional, for local HTTPS)
   - Provides HTTPS on 192.168.0.145
   - Self-signed certificate for local network access
   - Not required for public access
   - Config: `/etc/caddy/Caddyfile`

## Cloudflare Tunnel Setup

### Domain: meshcrawler.com
- **Registrar:** Namecheap
- **DNS:** Cloudflare (nameservers changed from AWS Route53)
- **Tunnel:** n8n-tunnel (cloudflared)
- **Public Hostname:** n8n.meshcrawler.com
- **Service:** http://localhost:5678

### Why Cloudflare Tunnel?
- No port forwarding needed
- Automatic HTTPS certificates
- DDoS protection
- Free tier is sufficient

### Steps Taken:
1. Created Cloudflare account
2. Added meshcrawler.com to Cloudflare (DNS records imported)
3. Changed Namecheap nameservers to Cloudflare
4. Created Cloudflare Tunnel (n8n-tunnel)
5. Installed cloudflared on VM
6. Configured public hostname route
7. Verified DNS propagation
8. Confirmed HTTPS working (certificate: Google Trust Services)

## Demo Workflows Created

### 1. Fetch Dad Joke
- **Type:** HTTP Request
- **Trigger:** Manual
- **Action:** GET https://icanhazdadjoke.com/
- **Result:** Extracts joke text and ID
- **Status:** ✅ Working

### 2. Execute CLI Commands
- **Type:** Execute Command (n8n-nodes-base.executeCommand)
- **Trigger:** Manual
- **Action:** Runs `uptime` command
- **Issue:** Node not recognized after initial import
- **Fix:** Restart n8n service to reload nodes
- **Status:** Fixed after restart

### 3. HTTP API Call
- **Type:** HTTP Request
- **Trigger:** Manual
- **Action:** GET https://api.github.com/users/octocat
- **Result:** Extracts username, profile URL, repo count
- **Status:** ✅ Working

## AI Integration Options

### Built-in AI Nodes:
- **OpenAI** — GPT-4, ChatGPT, DALL-E, embeddings
- **MistralAI** — Mistral models
- Both use no-code drag-and-drop interface

### Universal Approach: HTTP Request Node
Call any AI API:
- OpenAI API
- Anthropic Claude
- Google Gemini
- Local LLMs (Ollama, etc.)
- Custom AI endpoints
- Your own APIs!

**Key insight:** n8n is an orchestration layer. Your custom APIs on Proxmox VMs can be the backend services. n8n chains them together with HTTP Request nodes.

### Pattern: n8n + Custom APIs
```
Webhook trigger
  → HTTP Request (query your DB API)
  → HTTP Request (call your AI service)
  → HTTP Request (post to Slack)
```

## Instagram Integration

### Status: No Built-in Node
n8n does not have a native Instagram node.

### API Options:
- **Instagram Basic Display API** — Read-only, requires Facebook app
- **Instagram Graph API** — Business accounts only, requires verification
- Both require OAuth, app review, strict compliance

### Practical Alternatives:
1. **Third-party services** (easiest)
   - Apify (Instagram scrapers)
   - RapidAPI (Instagram endpoints)
   - Make/Zapier (limited integrations)

2. **Custom Python service** (flexible)
   - Use `instaloader` or `instagram-scraper` on a VM
   - Expose webhook endpoint
   - n8n calls the webhook

3. **RSS/IFTTT bridge**
   - Some Instagram-to-RSS services
   - IFTTT can trigger and call n8n webhooks

## Key Commands

```bash
# Restart n8n
ssh stephen@n8n-server "sudo systemctl restart n8n"

# Check n8n status
ssh stephen@n8n-server "sudo systemctl status n8n"

# Check cloudflared status
ssh stephen@n8n-server "sudo systemctl status cloudflared"

# View logs
ssh stephen@n8n-server "sudo journalctl -u n8n -f"
ssh stephen@n8n-server "sudo journalctl -u cloudflared -f"

# Update n8n
ssh stephen@n8n-server "sudo npm install -g n8n && sudo systemctl restart n8n"

# Test public URL
curl -s https://n8n.meshcrawler.com | head -5
```

## Security Notes

- n8n binds to localhost only (not exposed externally)
- Cloudflare Tunnel provides secure access
- Default credentials: admin/admin — should be changed
- SQLite database for default setup
- CLI commands run as stephen user (limited permissions)

## To Do

- [ ] Change default admin credentials
- [ ] Configure n8n for production use
- [ ] Set up automated backups
- [ ] Consider adding more integrations
- [ ] Explore custom API development on Proxmox VMs
- [ ] Instagram integration (requires third-party service or custom API)

## References

- n8n Documentation: https://docs.n8n.io
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Public URL: https://n8n.meshcrawler.com
- VM: n8n-server (192.168.0.145) on Proxmox seykhl

## Related Files

- N8N_SERVER.md — Full server documentation
- CLOUDFLARE_TUNNEL_SETUP.md — Tunnel setup guide
- README.md — Proxmox infrastructure overview
