# Mainland system monitor

Minimal Pacific-inspired host monitor with JSON as the public data format.

## Current output

`/home/ubuntu/system-monitor/system-current.json`

The JSON contains the current host reading plus rolling averages for:

- `1s`
- `1min`
- `5m`
- `15m`
- `30m`
- `1h`
- `3h`
- `6h`
- `12h`
- `24h`
- `3d`
- `7d`
- `1m` — one month
- `1y` — one year

Each average includes `sample_count`, `window_seconds`, and averaged numeric measurements.

## Storage

The monitor uses a local SQLite file internally:

`/home/ubuntu/system-monitor/system-monitor.sqlite3`

SQLite is only the rolling measurement engine. The monitor's exported/status data is JSON only.

The database automatically purges samples older than one year on every sampling run, so it cannot grow beyond the retention needed for the longest requested average.

No archive files, renamed snapshots, CSV files, or other persistent data formats are created.

## Sampling

Run:

`bash /home/ubuntu/system-monitor/sys-sample.sh`

Each run records one sample, recalculates all rolling averages, and atomically replaces `system-current.json`.
