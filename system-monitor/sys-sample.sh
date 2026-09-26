#!/usr/bin/env bash
set -euo pipefail
OUT="/home/ubuntu/system-monitor/system-current.json"
mkdir -p "$(dirname "$OUT")"
python3 - <<'PY'
import json, os, platform, shutil, time
from pathlib import Path
load1,load5,load15=os.getloadavg()
mem={}
for line in Path("/proc/meminfo").read_text().splitlines():
    k,v,*_=line.split(); mem[k.rstrip(":")]=int(v)*1024
root=shutil.disk_usage("/")
obj={
  "timestamp":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "hostname":platform.node(),
  "platform":platform.platform(),
  "uptime_seconds":float(Path("/proc/uptime").read_text().split()[0]),
  "load":{"1m":load1,"5m":load5,"15m":load15},
  "memory":{"total_bytes":mem.get("MemTotal",0),"available_bytes":mem.get("MemAvailable",0),"free_bytes":mem.get("MemFree",0)},
  "disk_root":{"total_bytes":root.total,"used_bytes":root.used,"free_bytes":root.free},
  "cpu_count":os.cpu_count(),
}
tmp=Path(str(Path(OUT).with_suffix(".tmp")))
tmp.write_text(json.dumps(obj,indent=2)+"\\n")
tmp.replace(OUT)
PY
