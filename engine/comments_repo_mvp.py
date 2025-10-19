from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
import json, random

def _root() -> Path:
    return Path(__file__).resolve().parents[1]

def _candidates(pack: str, lang: str) -> List[Path]:
    base = _root() / "assets" / "comments"
    names = [pack, f"{lang}_fun", "pl_fun", "fun"]
    tried, paths = set(), []
    for n in names:
        if not n or n in tried: 
            continue
        tried.add(n)
        paths += [base / f"{n}.json", Path.cwd() / "assets" / "comments" / f"{n}.json"]
    return paths

def _dedup(raw: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for k, vals in (raw or {}).items():
        seen, uniq = set(), []
        for v in vals:
            t = v.strip()
            key = t.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(t)
        out[k] = uniq
    return out

@dataclass
class CommentsRepoMVP:
    lang: str = "pl"
    pack: str = "pl_fun"
    rng: random.Random = field(default_factory=random.Random)
    no_repeat_window: int = 3

    _data: Dict[str, List[str]] = field(init=False, default_factory=dict)
    _recent: Dict[str, List[str]] = field(init=False, default_factory=dict)

    def load(self) -> None:
        for p in _candidates(self.pack, self.lang):
            if p.is_file():
                self._data = _dedup(json.loads(p.read_text(encoding="utf-8")))
                return
        raise FileNotFoundError(f"Brak paczki komentarzy (pack={self.pack}, lang={self.lang}).")

    def pick(self, key: str, **vars) -> str:
        vals = self._data.get(key) or []
        if not vals:
            return ""
        recent = self._recent.setdefault(key, [])
        pool = [v for v in vals if v not in recent[-self.no_repeat_window:]] or vals
        txt = self.rng.choice(pool)
        recent.append(txt)
        try:
            return txt.format(**vars)
        except Exception:
            return txt
