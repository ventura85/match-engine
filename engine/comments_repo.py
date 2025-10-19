from __future__ import annotations
import json
import random
from pathlib import Path
from typing import Dict, List

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "comments"
FUN_JSON = ASSETS_DIR / "fun.json"

class CommentsRepo:
    """Lekki loader komentarzy z JSON + anty-powtórki na poziomie kategorii."""
    _cache: Dict = {}
    _recent: Dict[str, List[int]] = {}
    _recent_limit: int = 5  # nie powtarzaj ostatnich n indeksów w kategorii

    @classmethod
    def load_fun(cls) -> Dict:
        if cls._cache.get("fun"):
            return cls._cache["fun"]
        try:
            data = json.loads(FUN_JSON.read_text(encoding="utf-8"))
            cls._cache["fun"] = data
            return data
        except Exception:
            # awaryjnie zwróć minimalny zestaw
            cls._cache["fun"] = {"build_up": {"short": ["{att} przy piłce."], "medium": ["{att} buduje."]}}
            return cls._cache["fun"]

    @classmethod
    def pick(cls, path: List[str]) -> str:
        """Wybór frazy z anty-powtórką. path np.: ['shot','on']"""
        data = cls.load_fun()
        node = data
        for p in path:
            node = node.get(p, {})
        if not isinstance(node, list):
            return ""
        n = len(node)
        if n == 0:
            return ""
        key = "/".join(path)
        recent = cls._recent.get(key, [])
        # wybierz indeks nieobecny w recent, jeśli możliwe
        candidates = [i for i in range(n) if i not in recent] or list(range(n))
        idx = candidates[random.randrange(len(candidates))]
        # aktualizuj recent
        recent.append(idx)
        if len(recent) > cls._recent_limit:
            recent = recent[-cls._recent_limit:]
        cls._recent[key] = recent
        return node[idx]
