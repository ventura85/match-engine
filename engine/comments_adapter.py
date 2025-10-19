from __future__ import annotations
from typing import List
from .comments_repo_mvp import CommentsRepoMVP

# Mapujemy nasze zdarzenia na możliwe klucze w paczce (z fallbackami).
KEYS = {
    "announce": ["announce", "offense", "akcja", "build_up"],
    "shot_saved": ["shot_saved", "save", "strzal_obroniony"],
    "shot_off": ["shot_off", "off_target", "strzal_obok"],
    "clearance": ["clearance", "wybicie", "def_clear"],
    "throw_in": ["throw_in", "aut", "wrzut_aut"],
    "corner_wasted": ["corner_wasted", "corner_lost", "rog_niewykorzystany"],
    "goal": ["goal", "gol"],
}

DEFAULTS = {
    "announce": ["• {team} w ofensywie…"],
    "shot_saved": ["➜ strzał obroniony."],
    "shot_off": ["➜ strzał obok."],
    "clearance": ["➜ wybicie."],
    "throw_in": ["➜ aut."],
    "corner_wasted": ["➜ róg niewykorzystany."],
    "goal": ["➜ GOL! {team} prowadzi {scoreA}:{scoreB}."],
}

class Comments:
    def __init__(self, pack: str = "pl_fun", lang: str = "pl", no_repeat_window: int = 3):
        self.repo = CommentsRepoMVP(lang=lang, pack=pack, no_repeat_window=no_repeat_window)
        self.repo.load()

    def _pick(self, kind: str, **kw) -> str:
        for key in KEYS[kind]:
            t = self.repo.pick(key, **kw)
            if t:
                return t
        # fallback tekst
        import random
        return random.choice(DEFAULTS[kind]).format(**kw)

    # API używane przez silnik
    def announce(self, *, team: str, minute: str) -> str:
        return self._pick("announce", team=team, minute=minute)

    def goal(self, *, team: str, minute: str, scoreA: int, scoreB: int) -> str:
        return self._pick("goal", team=team, minute=minute, scoreA=scoreA, scoreB=scoreB)

    def shot_saved(self, *, team: str, minute: str) -> str:
        return self._pick("shot_saved", team=team, minute=minute)

    def shot_off(self, *, team: str, minute: str) -> str:
        return self._pick("shot_off", team=team, minute=minute)

    def clearance(self, *, team: str, minute: str) -> str:
        return self._pick("clearance", team=team, minute=minute)

    def throw_in(self, *, team: str, minute: str) -> str:
        return self._pick("throw_in", team=team, minute=minute)

    def corner_wasted(self, *, team: str, minute: str) -> str:
        return self._pick("corner_wasted", team=team, minute=minute)
