# Cloudflare Tunnel Setup for meshcrawler.com

## Step 1: Create Cloudflare Account & Tunnel

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Add your domain: `meshcrawler.com`
3. Cloudflare will scan existing DNS records. Review them.
4. Go to the DNS tab and add a CNAME record:
   - **Name:** `n8n` (or root `@` if you want n8n at the root domain)
   - **Target:** `your-tunnel-subdomain.cfargotunnel.com` (this will be shown after you create the tunnel)
   - **Proxy status:** Proxied (orange cloud)

## Step 2: Create a Cloudflare Tunnel

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. In the left sidebar, click **Zero Trust** (you might need to sign up for the free Zero Trust plan — it's free)
3. Click **Networks** in the left sidebar
4. Click **Tunnels** in the dropdown
5. Click the **Create a tunnel** button (blue button)
6. Choose **Cloudflared** as the connector type
7. Give it a name (e.g., `n8n-tunnel`) and click **Save tunnel**
8. You'll see a page that says "Choose your environment" with a command:
   ```
   cloudflared.exe service install YOUR_TOKEN_HERE
   ```
   **Copy that long token string** (it looks like `eyJhIjoi...` and is very long)
   
   **Important:** The token is the secret that connects your VM to Cloudflare. Keep it safe.

## Step 3: Configure Public Hostnames

In the tunnel configuration, add a **Public Hostname**:
- **Subdomain:** `n8n` (or leave blank for root)
- **Domain:** `meshcrawler.com`
- **Service:** `http://localhost:5678`
- **Status:** Active

## Step 4: Update Namecheap DNS

1. Go to [Namecheap Dashboard](https://ap.www.namecheap.com)
2. Find `meshcrawler.com` and click **Manage**
3. Go to **Nameservers**
4. Change from AWS Route53 to **Cloudflare nameservers** (they'll be provided after you add the domain to Cloudflare)
5. Save changes. DNS propagation takes 5-30 minutes.

## Step 5: Configure cloudflared on n8n VM ✅ DONE

The cloudflared service is installed and running on the VM. Status:
- Service: `active (running)`
- Connected to Cloudflare: ✅
- Tunnel protocol: QUIC

To verify it's running:
```bash
ssh stephen@192.168.0.145 "sudo systemctl status cloudflared"
```

## Step 6: Verify

Once everything is running:
- Visit `https://n8n.meshcrawler.com` (or whatever subdomain you set up)
- You should see the n8n login page with a valid HTTPS certificate

## Notes
- Cloudflare Tunnel handles HTTPS automatically — no Caddy needed for this approach
- You can disable the Caddy service if you want to use Cloudflare Tunnel exclusively:
  ```bash
  sudo systemctl disable caddy
  sudo systemctl stop caddy
  ```
- The tunnel connects *outbound* from the VM to Cloudflare, so no port forwarding is needed

## Troubleshooting
- Check tunnel status: `sudo journalctl -u cloudflared -f`
- Check Cloudflare dashboard for tunnel status
- Verify DNS is pointing to Cloudflare: `dig n8n.meshcrawler.com`
