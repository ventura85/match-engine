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
    no_repeat_window: int = 5

    _data: Dict[str, List[str]] = field(init=False, default_factory=dict)
    _recent: Dict[str, List[str]] = field(init=False, default_factory=dict)
    _cooldown: Dict[str, Dict[str, int]] = field(init=False, default_factory=dict)  # key -> text -> ticks

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
        # Support optional weighted entries as {"text":..., "weight":...}
        items = []  # list of (text, weight)
        for v in vals:
            if isinstance(v, dict):
                t = str(v.get('text', '')).strip()
                w = float(v.get('weight', 1.0))
            else:
                t = str(v).strip()
                w = 1.0
            if not t:
                continue
            items.append((t, w))
        recent = self._recent.setdefault(key, [])
        cooldown = self._cooldown.setdefault(key, {})
        # Decay cooldowns
        for k in list(cooldown.keys()):
            cooldown[k] = max(0, cooldown[k] - 1)
            if cooldown[k] == 0:
                cooldown.pop(k, None)
        # Build pool with anti-repeat and cooldown weight penalty
        pool = []
        for (t, w) in items:
            if t in recent[-self.no_repeat_window:]:
                continue
            pen = 0.5 if t in cooldown else 1.0
            pool.append((t, max(0.0, w * pen)))
        if not pool:
            pool = items
        # Weighted choice
        total = sum(w for _, w in pool)
        if total <= 0:
            txt = self.rng.choice([t for t, _ in pool])
        else:
            r = self.rng.random() * total
            acc = 0.0
            txt = pool[-1][0]
            for t, w in pool:
                acc += w
                if r <= acc:
                    txt = t
                    break
        recent.append(txt)
        cooldown[txt] = 2  # temporary deprecation
        try:
            return txt.format(**vars)
        except Exception:
            return txt
