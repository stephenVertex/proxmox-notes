# Plan: Activate the Sefer Dolt live read replica

**Created:** 2026-08-27  
**Status:** Approved as a plan; execution not started  
**Change window:** Reserve 30–45 minutes; expected interruption should be
shorter after rehearsal

## Goal

Turn `doltsvr-sefer` (`192.168.0.160`) from a validated static snapshot into a
live Dolt direct-to-standby replica of production `doltsvr`
(`192.168.0.150`). During burn-in, production remains the only write primary
and analytics uses a separate, read-only endpoint on Sefer.

This plan does not move the canonical `doltsvr` identity or promote Sefer to
primary. That remains a later, separately approved cutover.

## Current state

| Component | Current state | Required activation state |
|---|---|---|
| Production | Dolt 2.1.10, unclustered write primary | Dolt 2.3.1, cluster primary, epoch 1 |
| Sefer VM 100 | Dolt 2.3.1, validated static seed | Dolt 2.3.1, cluster standby, epoch 1 |
| Data | 34 validated repositories from the 2026-08-27 cold seed | Final cold refresh immediately before activation |
| Replication | None | Paired per-database remotes over TCP 50051 |
| Sefer SQL | Service disabled and inactive; port 3306 closed | Running standby; 3306 open only to approved analytics sources |
| Credentials | Seeded production accounts only | Dedicated least-privilege analytics account on both nodes |
| Monitoring | Offline validation only | Role, epoch, lag, error, service, and disk monitoring |

The existing seed is an integrity-proven starting point, not the activation
seed. Production resumed after it was taken, so a final cold refresh is
required before the replication cluster starts.

## Safety invariants

- `192.168.0.150` remains the only write endpoint throughout activation and
  burn-in.
- Do not assign Sefer the production hostname, mDNS identity, Tailscale
  identity, or canonical client route.
- Keep application writers paused from the final cold refresh until all
  acceptance gates pass.
- Never start both nodes as `primary` in the same epoch.
- Do not expose Sefer port 3306 before its role is confirmed as `standby` and
  replication is clean for all databases.
- TCP 50051 is peer-only: `.150` may reach `.160`, and `.160` may reach `.150`.
- Do not perform a one-sided snapshot restore after new writes have resumed;
  that could discard acknowledged writes or create divergent cluster state.
- No password or other secret belongs in this repository.

## Decisions required before execution

1. Approve the maintenance date and writer-pause window.
2. Supply the exact analytics source IP or CIDR allowed to reach Sefer port
   3306.
3. Choose how the generated analytics credential will be handed off.
4. Approve the tested value for
   `dolt_cluster_ack_writes_timeout_secs`. A nonzero value improves standby
   acknowledgement guarantees but can add primary write latency; benchmark it
   during rehearsal before fixing the production value.

## Phase 1: No-outage preparation and rehearsal

These steps must not change the running production service.

1. Reconfirm the production service, Dolt version, data directory, database
   inventory, free space, current connections, and backup health.
2. Rehearse a two-node Dolt 2.3.1 cluster with disposable copies of the data.
3. Generate configuration files for these fixed roles:
   - Seykhl `192.168.0.150`: `primary`, bootstrap epoch `1`
   - Sefer `192.168.0.160`: `standby`, bootstrap epoch `1`
4. Generate and audit one peer remote for every existing Dolt repository. Dolt
   requires databases that exist before cluster startup to have a corresponding
   configured standby remote.
5. Test cluster startup with the standby first and the primary second.
6. Test a dedicated canary database from creation through replication and
   cleanup. Because `DROP DATABASE` is not replicated, perform and verify its
   cleanup on both nodes.
7. Test the monitoring queries, standby write rejection, standby restart, and
   catch-up behavior.
8. Prepare exact apply and rollback commands. Validate the YAML and systemd
   units without starting production cluster mode.

### Phase 1 gate

- Both rehearsal nodes report the intended roles and epoch.
- Every database reports zero lag and no current error.
- A canary write appears on the standby.
- A client write to the standby is rejected.
- Restarting the rehearsal standby returns it to zero lag.
- The production service remains unchanged and active.

## Phase 2: Maintenance-window activation

1. Pause all writers and verify that application traffic has quiesced.
2. Stop production `dolt-sql-server` gracefully.
3. Take a new rollback snapshot and cold NAS backup of the stopped production
   VM. Record their exact identifiers before continuing.
4. Pin production to the same verified Dolt 2.3.1 binary as Sefer. Preserve
   the 2.1.10 binary and old service definition for rollback.
5. Refresh Sefer from the stopped production data, preserving branches,
   working sets, server privilege data, ownership, and modes.
6. Prove the refresh is byte-identical with a checksum-mode dry run, then run
   the repository validator.
7. Add the paired replication remote to every existing repository:
   - Production remote template targets
     `http://192.168.0.160:50051/{database}`.
   - Sefer remote template targets
     `http://192.168.0.150:50051/{database}`.
8. Install the reviewed cluster YAML and config-driven systemd unit on
   production. Install the matching standby YAML on Sefer.
9. Open TCP 50051 only between the two exact peer IPs. Keep Sefer port 3306
   closed to analytics.
10. Start Sefer first and confirm it is `standby`, epoch `1`.
11. Start production and confirm it is `primary`, epoch `1`.
12. Keep writers paused while the activation acceptance checks run.

### Phase 2 acceptance checks

```sql
SELECT @@GLOBAL.dolt_cluster_role,
       @@GLOBAL.dolt_cluster_role_epoch;

SELECT *
FROM dolt_cluster.dolt_cluster_status;
```

Require all of the following:

- Production role is `primary`; Sefer role is `standby`; both are epoch `1`.
- Every expected database is present on both nodes.
- Every primary status row has `replication_lag_millis = 0`.
- Every primary status row has `current_error IS NULL`.
- Representative branch heads, issue counts, and recent data match.
- A controlled canary transaction on production appears on Sefer.
- The same write attempted through Sefer is rejected.
- Existing production clients reconnect and pass read/write smoke checks.

Only after every check passes may writers resume.

## Phase 3: Analytics endpoint

1. Create a dedicated `analytics_ro` account with only the required `SELECT`
   and metadata-view permissions. Apply and verify the account on both nodes;
   do not assume users and grants replicate.
2. Open Sefer TCP 3306 only from the approved analytics IP or CIDR.
3. Confirm the account can read permitted databases and cannot write, create,
   alter, drop, grant, or invoke cluster role changes.
4. Hand off:

   ```text
   Host: 192.168.0.160
   Port: 3306
   Protocol: MySQL
   User: analytics_ro
   ```

5. Keep all application writers on production `192.168.0.150`.

## Phase 4: Burn-in

Run the direct standby for at least 24–72 hours before considering migration
of the primary role.

Monitor and alert on:

- no configured primary;
- a role other than the intended `primary`/`standby` pair;
- `detected_broken_config` on either node;
- NULL or growing `replication_lag_millis`;
- non-NULL `current_error`;
- systemd service failures or restarts;
- disk capacity and backup failures;
- primary write-latency changes after acknowledgement settings are enabled.

During burn-in, restart the standby once in a controlled test and prove that it
returns to zero lag. Record a failover drill separately; do not promote Sefer
as part of this activation plan.

## Rollback

### Before writers resume

1. Keep writers paused.
2. Stop both Dolt services.
3. Close the new 3306 and 50051 firewall rules.
4. Restore production's pre-change binary, service definition, configuration,
   and cold snapshot or backup.
5. Start production alone on 2.1.10 and verify existing clients.
6. Return Sefer to disabled, inactive, isolated static-snapshot state.
7. Resume writers only after the old primary passes its smoke checks.

### After writers resume

Do not restore an old snapshot on either node independently. Pause writers,
capture both nodes' role, epoch, replication status, and newest commit state,
then choose a coherent cluster recovery point. A stale one-sided restore can
lose writes or create divergence.

## Completion criteria

This plan is complete when:

- production remains the write primary on `192.168.0.150`;
- Sefer continuously serves current reads on `192.168.0.160`;
- all 34 existing repositories and newly created databases replicate;
- lag is zero at steady state and alerts cover the documented failure modes;
- the analytics account is least-privilege and network-restricted;
- standby restart and catch-up have been demonstrated;
- rollback artifacts and their retention window are recorded;
- the canonical `doltsvr` identity has not moved.

## Future controlled cutover

The later migration to Sefer as primary is out of scope here. It will require a
new writer pause, zero-lag verification, a graceful epoch increase using
`dolt_assume_cluster_role`, client routing changes, and a defined soak period
with the old server retained as rollback standby.

## References

- [Current Sefer standby runbook](DOLT_STANDBY.md)
- [Production Dolt runbook](DOLT_SERVER.md)
- [Dolt direct-to-standby replication](https://www.dolthub.com/docs/sql-reference/server/replication/)
- [Dolt server configuration](https://www.dolthub.com/docs/sql-reference/server/configuration/)
- [Dolt system variables](https://www.dolthub.com/docs/sql-reference/version-control/dolt-sysvars/)
- [Dolt 2.3.1 release](https://github.com/dolthub/dolt/releases/tag/v2.3.1)
