# Hawaii local-data-globe collector

Headless Hawaii telemetry exporter for the Network Globe project.

Project location on the Hawaii machine:
`/home/rootrecord/.ollama/skills/local-data-globe` (confirm this is still the
right location when this is actually deployed — it may end up living under
`coms/ssh` instead now that the skill layout has changed since this was last
live; see `RATIONALE.md`)

The collector observes real local network sockets (`ss`) and optional packet
metadata (`tcpdump`), normalizes observations as NDJSON, and streams them
**live** to the existing AWS Network Globe project over SSH.

It does not contain a visualizer or a second poller.

## Design principle: live state, not stored history

AWS is a live mirror, not a data store. This collector never gives it
anything to "catch up" on:

- **SSH reachable:** every record streams to AWS the moment it's observed.
- **SSH unreachable, general internet still up:** the record is handed to
  `telegram-relay.js` instead, which batches in memory (never to disk) and
  ships it as a zip to the existing "Root Record Data Relay" Telegram
  channel — off-box insurance only.
- **No internet at all:** the record simply isn't sent anywhere. It is not
  queued to disk for later replay.
- **On reconnect:** the collector resumes live pushes only. There is no
  backfill step. A gap in local connectivity should show up on the globe as
  a gap — no data from Hawaii during that window — not as a delayed catch-up
  dump. **Telegram's copy of what happened during the gap is never fed back
  into AWS, on reconnect or otherwise.** It exists purely for your own later
  reference if you need to know what was missed.

See `RATIONALE.md` for the fuller reasoning and what changed from the
previous version of this collector.

## System requirements

- `ss` (iproute2) — flow observation
- `tcpdump` — optional, only used if running as root
- `ssh`, and `cloudflared` at `/home/rootrecord/.local/bin/cloudflared`
  (or update the hardcoded path in `sshArgs()`) — for the
  `ssh.rootrecord.cloud` proxy path
- `zip` (CLI) — used by `telegram-relay.js` to build the insurance
  packs; not an npm dependency, needs to be installed on the box
- Node 18+ (uses built-in `fetch`, `FormData`, `Blob`, `AbortSignal.timeout`)

## AWS transport

Default AWS endpoint is **`ssh.rootrecord.cloud`**, not a raw IP — the SSH
connection is proxied through Cloudflare Access
(`cloudflared access ssh --hostname %h`) specifically because AWS's IP is
dynamic. Confirm `cloudflared` is actually installed and authenticated at
`/home/rootrecord/.local/bin/cloudflared` on whatever box runs this before
relying on it — that path is hardcoded in `sshArgs()`.

The default SSH key is `/home/rootrecord/.ssh/rootrecordkey.pem`. The key
path is explicit because `start.sh` runs the collector with sudo, so the
collector cannot rely on the user's `~/.ssh/config` or SSH agent.

Remote destination:
`/home/ubuntu/network-globe/network-globe/data/hawaii.ndjson`

## Telegram insurance relay

See `telegram-relay.js`. Needs `TELEGRAM_RELAY_CHAT_ID` set to the "Root
Record Data Relay" channel id (kept separate from `RR_CONTROL_CHAT_ID` and
`RR_PUBLISH_CHAT_ID` — do not reuse those). Bot token loads from
`/home/rootrecord/master/master-key.env`, same convention as `coms/telegram`.

Batches flush every `TELEGRAM_BATCH_MS` (default 15 min, matching the
channel's existing cadence) or at `TELEGRAM_BATCH_MAX_RECORDS` (default
5000), whichever comes first. Filenames match the existing channel
convention: `rootrecord-YYYYMMDD-HHMM-<hash>.zip`.

If Telegram send fails too (no internet), the in-memory batch for that
window is dropped — not retried, not written to disk. That's an accepted
tradeoff of "never accumulate," not an oversight; see `RATIONALE.md` if you
want to revisit it.

## What this explicitly does NOT do (changed from the previous version)

The version of this collector that ran before — see `git blame` / the
`online-safe-20260920` backup this was recovered from — buffered
undelivered records to `data/outbox.ndjson` on disk and replayed them into
AWS once SSH reconnected. **That behavior has been removed.** It
contradicted the live-only requirement: AWS should never receive a delayed
dump of what it missed. If you find yourself wanting that behavior back,
that's a real design conversation to have again, not something to
silently restore.

## AWS feed retention / disk safety

`hawaii.ndjson` is a live feed, not a permanent archive. The collector now bounds it at 64 MiB by default and trims it back to a 48 MiB complete-record window when needed.

The collector deliberately closes the SSH append stream before invoking `maintain-hawaii-feed.sh` on AWS. The maintenance script rewrites the **same inode**, then resets only the byte offset in `hawaii-offset.json`. It does not rename the live feed, preserving the reader's expected pathname and avoiding an open-file/renamed-file leak.

The thresholds are configurable with:

- `AWS_FEED_MAX_BYTES` — default `67108864` (64 MiB)
- `AWS_FEED_TARGET_BYTES` — default `50331648` (48 MiB)
- `AWS_FEED_MAINTENANCE_MS` — default 15 minutes
- `AWS_FEED_MAINTENANCE_SCRIPT` — default `/home/ubuntu/network-globe/network-globe/scripts/maintain-hawaii-feed.sh`

The AWS-side script should be deployed to that path. It is intentionally kept separate from the collector so mainland maintenance can be inspected and backed up independently.

### Mainland deployment

From the Hawaii machine, after syncing `main`, deploy the maintenance helper to AWS with:

```bash
ssh rr-aws 'mkdir -p /home/ubuntu/network-globe/network-globe/scripts /home/ubuntu/network-globe/backups && if [ -f /home/ubuntu/network-globe/network-globe/scripts/maintain-hawaii-feed.sh ]; then cp -a /home/ubuntu/network-globe/network-globe/scripts/maintain-hawaii-feed.sh /home/ubuntu/network-globe/backups/maintain-hawaii-feed.sh.bak-$(date +%Y%m%d-%H%M%S); fi && if [ -f /home/ubuntu/network-globe/network-globe/data/hawaii-offset.json ]; then cp -a /home/ubuntu/network-globe/network-globe/data/hawaii-offset.json /home/ubuntu/network-globe/backups/hawaii-offset.json.bak-$(date +%Y%m%d-%H%M%S); fi' && \
ssh rr-aws 'cat > /home/ubuntu/network-globe/network-globe/scripts/maintain-hawaii-feed.sh' < coms/ssh/local-data-globe/maintain-hawaii-feed.sh && \
ssh rr-aws 'chmod 0755 /home/ubuntu/network-globe/network-globe/scripts/maintain-hawaii-feed.sh && /home/ubuntu/network-globe/network-globe/scripts/maintain-hawaii-feed.sh 67108864 50331648'
```

The first deployment is intentionally one-shot. The collector owns the cadence thereafter; it probes the remote feed size every 15 minutes and only interrupts its SSH stream when the 64 MiB ceiling is exceeded.
