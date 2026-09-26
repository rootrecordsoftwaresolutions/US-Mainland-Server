#!/usr/bin/env bash
set -euo pipefail

OUT="/home/ubuntu/system-monitor/system-current.json"
DB="/home/ubuntu/system-monitor/system-monitor.sqlite3"

mkdir -p "$(dirname "$OUT")"

python3 - "$OUT" "$DB" <<'PY'
import json
import os
import platform
import shutil
import sqlite3
import sys
import time
from pathlib import Path

OUT = Path(sys.argv[1])
DB = Path(sys.argv[2])

# Rolling windows. "1m" is one month; "1min" is one minute.
WINDOWS = {
    "1s": 1,
    "1min": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "3h": 10800,
    "6h": 21600,
    "12h": 43200,
    "24h": 86400,
    "3d": 259200,
    "7d": 604800,
    "1m": 2592000,
    "1y": 31536000,
}
RETENTION_SECONDS = WINDOWS["1y"]

now = time.time()
load1, load5, load15 = os.getloadavg()

mem = {}
for line in Path("/proc/meminfo").read_text().splitlines():
    k, v, *_ = line.split()
    mem[k.rstrip(":")] = int(v) * 1024

root = shutil.disk_usage("/")
sample = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "timestamp_unix": now,
    "hostname": platform.node(),
    "platform": platform.platform(),
    "load": {"1m": load1, "5m": load5, "15m": load15},
    "memory": {
        "total_bytes": mem.get("MemTotal", 0),
        "available_bytes": mem.get("MemAvailable", 0),
        "free_bytes": mem.get("MemFree", 0),
    },
    "disk_root": {
        "total_bytes": root.total,
        "used_bytes": root.used,
        "free_bytes": root.free,
    },
    "cpu_count": os.cpu_count(),
    "uptime_seconds": float(Path("/proc/uptime").read_text().split()[0]),
}

DB.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(DB) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            timestamp REAL PRIMARY KEY,
            load_1m REAL NOT NULL,
            load_5m REAL NOT NULL,
            load_15m REAL NOT NULL,
            memory_total_bytes INTEGER NOT NULL,
            memory_available_bytes INTEGER NOT NULL,
            memory_free_bytes INTEGER NOT NULL,
            disk_total_bytes INTEGER NOT NULL,
            disk_used_bytes INTEGER NOT NULL,
            disk_free_bytes INTEGER NOT NULL,
            cpu_count INTEGER NOT NULL,
            uptime_seconds REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp)")

    conn.execute("""
        INSERT OR REPLACE INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now,
        load1, load5, load15,
        mem.get("MemTotal", 0),
        mem.get("MemAvailable", 0),
        mem.get("MemFree", 0),
        root.total,
        root.used,
        root.free,
        os.cpu_count() or 0,
        sample["uptime_seconds"],
    ))

    # Keep exactly enough history to answer the longest requested window.
    conn.execute("DELETE FROM samples WHERE timestamp < ?", (now - RETENTION_SECONDS,))
    conn.commit()

    averages = {}
    numeric_columns = {
        "load_1m": "load.1m",
        "load_5m": "load.5m",
        "load_15m": "load.15m",
        "memory_total_bytes": "memory.total_bytes",
        "memory_available_bytes": "memory.available_bytes",
        "memory_free_bytes": "memory.free_bytes",
        "disk_total_bytes": "disk_root.total_bytes",
        "disk_used_bytes": "disk_root.used_bytes",
        "disk_free_bytes": "disk_root.free_bytes",
        "uptime_seconds": "uptime_seconds",
    }

    for label, seconds in WINDOWS.items():
        cutoff = now - seconds
        row = conn.execute(
            """
            SELECT COUNT(*),
                   AVG(load_1m), AVG(load_5m), AVG(load_15m),
                   AVG(memory_total_bytes), AVG(memory_available_bytes),
                   AVG(memory_free_bytes), AVG(disk_total_bytes),
                   AVG(disk_used_bytes), AVG(disk_free_bytes),
                   AVG(uptime_seconds)
            FROM samples
            WHERE timestamp >= ?
            """,
            (cutoff,),
        ).fetchone()

        count = row[0]
        values = {}
        for i, (column, key) in enumerate(numeric_columns.items(), start=1):
            if row[i] is not None:
                values[key] = row[i]

        averages[label] = {
            "sample_count": count,
            "window_seconds": seconds,
            "values": values,
        }

result = {
    **{k: v for k, v in sample.items() if k != "timestamp_unix"},
    "averages": averages,
}

tmp = OUT.with_suffix(".tmp")
tmp.write_text(json.dumps(result, indent=2) + "\n")
tmp.replace(OUT)
PY
