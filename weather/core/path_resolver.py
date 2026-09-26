"""URL -> deterministic *_current path. No archive/history path exists here."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit
DEFAULT_EXT="txt"
@dataclass(frozen=True)
class ResolvedResource:
    host:str; resource_dir:str; name:str; ext:str
    def base_dir_relative(self)->str:return f"{self.host}/{self.resource_dir}"
    def current_path(self,base_dir:str)->str:return f"{base_dir}/{self.base_dir_relative()}/{self.name}_current.{self.ext}"
def _name_and_ext_from_path(path:PurePosixPath)->tuple[str,str]:
    stem=path.stem; suffix=path.suffix.lstrip(".")
    if not stem:return "index",suffix or DEFAULT_EXT
    return stem,suffix or DEFAULT_EXT
def resolve(url:str,resource_id_hint:str|None=None)->ResolvedResource:
    parts=urlsplit(url); host=parts.netloc or "www.weather.gov"
    if host.startswith("www."):host=host[4:]
    path=PurePosixPath(parts.path)
    if parts.query:
        qname=resource_id_hint or parts.query
        parent=str(path).lstrip("/")
        resource_dir=f"{parent}/{qname}" if parent else qname
        ext="json" if "api.weather.gov" in host else "html"
        return ResolvedResource(host,resource_dir,qname,ext)
    name,ext=_name_and_ext_from_path(path); parent=str(path.parent).lstrip("/")
    resource_dir=f"{parent}/{name}" if parent and parent!="." else name
    return ResolvedResource(host,resource_dir,name,ext)
