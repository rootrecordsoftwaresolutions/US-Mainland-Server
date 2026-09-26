"""Mainland current-only weather poller."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scheduler.run_cycle import run_forever
if __name__=="__main__":run_forever(sys.argv[1] if len(sys.argv)>1 else "/home/ubuntu/weather-data",30.0)
