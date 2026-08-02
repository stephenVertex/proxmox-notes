# dynamodb — Amazon DynamoDB Local (LXC)

## Overview
`dynamodb` (CTID 115) is an unprivileged LXC container running
[Amazon DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html),
the official local build of DynamoDB for development and testing. No AWS
account, credentials, or network egress required — any access key/secret
values are accepted.

## Container Specifications
| Setting | Value |
|---------|-------|
| **CTID** | 115 |
| **Hostname** | dynamodb |
| **Type** | LXC (unprivileged) |
| **OS** | Debian 12 "Bookworm" (template `debian-12-standard_12.12-1`) |
| **Cores** | 1 |
| **Memory** | 1GB (+512MB swap) — actual usage ~220MB |
| **Disk** | 8GB (local-lvm) |
| **Network** | vmbr0, DHCP |
| **LAN IP** | 192.168.0.144 |
| **Status** | Running (`--onboot 1`) |

## Endpoint

- **URL:** `http://192.168.0.144:8000` or `http://dynamodb.local:8000`
- **Name resolution:** mDNS via `avahi-daemon` — macOS/Linux resolve
  `dynamodb.local` with zero client config; **no /etc/hosts entry needed**
- **Auth:** any dummy credentials work (e.g. `AWS_ACCESS_KEY_ID=fake AWS_SECRET_ACCESS_KEY=fake`)
- **Region:** any (use `us-east-1` for consistency)

### Usage Examples

```bash
export AWS_ACCESS_KEY_ID=fake AWS_SECRET_ACCESS_KEY=fake AWS_REGION=us-east-1
export AWS_ENDPOINT_URL_DYNAMODB=http://192.168.0.144:8000   # aws-cli v2.22+

aws dynamodb list-tables
aws dynamodb create-table \
  --table-name my-table \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

Or per-call without the env var:

```bash
aws dynamodb list-tables --endpoint-url http://192.168.0.144:8000
```

SDKs: point the DynamoDB client at `endpoint_url=http://192.168.0.144:8000`
(boto3), `endpointOverride` (AWS SDK for Java v2), or `endpoint` in the
client config (SDK for JS v3 / .NET / Go).

## Installation Details

- **Runtime:** OpenJDK 17 (`openjdk-17-jre-headless`)
- **Install dir:** `/opt/dynamodb` (jar + `DynamoDBLocal_lib`), from
  `https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz`
- **Data dir:** `/var/lib/dynamodb` (persistent, `-sharedDb` mode — one
  database file shared across all credentials/regions)
- **Service user:** `dynamodb` (system user, nologin)
- **systemd unit:** `/etc/systemd/system/dynamodb-local.service`
  (enabled, `Restart=always`, JVM capped at `-Xmx512m`)

## Management

```bash
# Console / shell (from Proxmox host)
ssh seykhl "pct enter 115"

# Service control
ssh seykhl "pct exec 115 -- systemctl status dynamodb-local"
ssh seykhl "pct exec 115 -- systemctl restart dynamodb-local"
ssh seykhl "pct exec 115 -- journalctl -u dynamodb-local -f"

# Container control
ssh seykhl "pct stop 115 && pct start 115"

# Wipe all local data (tables are recreated by your app/tests)
ssh seykhl "pct exec 115 -- bash -c 'systemctl stop dynamodb-local && rm -f /var/lib/dynamodb/*.db && systemctl start dynamodb-local'"
```

## Upgrading DynamoDB Local

```bash
ssh seykhl "pct exec 115 -- bash -c '\
  systemctl stop dynamodb-local && \
  curl -fsSL https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz -o /tmp/ddb.tar.gz && \
  tar -xzf /tmp/ddb.tar.gz -C /opt/dynamodb && rm /tmp/ddb.tar.gz && \
  chown -R dynamodb:dynamodb /opt/dynamodb && \
  systemctl start dynamodb-local'"
```

## Notes

- **Router DHCP reservation:** the container is a DHCP client (matches the
  rest of the fleet). Router assigned 192.168.0.144 on 2026-08-02; add a
  MAC/IP reservation on the router (`BC:24:11:A3:EA:0D` → 192.168.0.144,
  like the other cluster entries in `Address_Reservation_List-*.csv`) so the
  lease never drifts.
- Health check: `curl http://192.168.0.144:8000/` returning HTTP 400 with a
  `MissingAuthenticationToken` JSON body means the service is up and healthy.
- Not in Tailscale; LAN-only by design (dev/test datastore).
