"""Current-only weather scheduler."""
from __future__ import annotations
import time,traceback
from concurrent.futures import ThreadPoolExecutor
from core import hst_time
from core.manifest import Manifest
from scheduler import tiers
from fetch import alerts,analyses,aviation,climate,maps,marine,ndfd_gridpoint,radar,satellite,text_products,misc,gis
FETCH_MODULES={"alerts":alerts.fetch_all,"text_products":text_products.fetch_all,"satellite":satellite.fetch_all,"analyses":analyses.fetch_all,"radar":radar.fetch_all,"marine":marine.fetch_all,"aviation":aviation.fetch_all,"climate":climate.fetch_all,"maps":maps.fetch_all,"ndfd_gridpoint":ndfd_gridpoint.fetch_all,"misc":misc.fetch_all,"gis":gis.fetch_all}
def _log(m):print(f"{hst_time.hst_now().isoformat(timespec='seconds')} {m}",flush=True)
class SchedulerState:
 def __init__(self):self.last={}
def run_once(state,base_dir):
 m=Manifest(base_dir);now=time.monotonic();due=[(n,f) for n,f in FETCH_MODULES.items() if tiers.is_due(last_run_monotonic=state.last.get(n),now_monotonic=now,tier=tiers.module_tier(n))]
 def one(item):
  n,f=item
  try:
   for o in f(m,base_dir):
    if o.status in ("failed","invalid"):_log(f"module:{n} resource:{o.resource_id} {o.status.upper()} -- {o.detail}")
  except Exception:_log(f"module:{n} ERROR (continuing)\n{traceback.format_exc()}")
  finally:state.last[n]=time.monotonic()
 with ThreadPoolExecutor(max_workers=min(16,max(1,len(due)))) as p:[x.result() for x in [p.submit(one,d) for d in due]]
def run_forever(base_dir,tick_seconds=30.0):
 s=SchedulerState()
 while True:
  try:run_once(s,base_dir)
  except Exception:_log("scheduler ERROR (continuing)\n"+traceback.format_exc())
  time.sleep(tick_seconds)
