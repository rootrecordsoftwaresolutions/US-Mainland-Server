"""In-memory resource state only. No manifest file is written."""
from __future__ import annotations
import threading
from dataclasses import dataclass,asdict
from typing import Any
@dataclass
class ResourceState:
    resource_id:str; url:str; local_resource_dir:str
    current_fetch_timestamp_hst:str|None=None; etag:str|None=None; last_modified:str|None=None
    content_length:int|None=None; content_sha256:str|None=None; consecutive_failures:int=0
    last_failure_at:str|None=None; last_success_at:str|None=None
    def to_dict(self)->dict[str,Any]:return asdict(self)
class Manifest:
    def __init__(self,base_dir:str):self._data={};self._lock=threading.Lock()
    def load(self):return self
    def save(self):return None
    def get_or_create(self,rid,url,local_resource_dir):
        with self._lock:
            if rid not in self._data:self._data[rid]=ResourceState(rid,url,local_resource_dir)
            return self._data[rid]
    def record_success(self,rid,**kw):
        with self._lock:
            s=self._data[rid]
            for k,v in kw.items():
                if hasattr(s,k):setattr(s,k,v)
            s.consecutive_failures=0
    def record_unchanged(self,rid,**kw):
        with self._lock:self._data[rid].last_success_at=kw.get("confirmed_at_hst_iso");self._data[rid].consecutive_failures=0
    def record_failure(self,rid,**kw):
        with self._lock:self._data[rid].consecutive_failures+=1;self._data[rid].last_failure_at=kw.get("failed_at_hst_iso")
