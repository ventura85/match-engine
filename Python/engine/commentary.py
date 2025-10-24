from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class RecentCache:
    """
    Globalny cache ostatnich fraz (global cooldown). Przechowuje ostatnie N
    użytych stringów, by nie powtarzać ich zbyt gęsto niezależnie od kategorii.
    """
    maxlen: int = 50
    _dq: Deque[str] = field(default_factory=deque, init=False)

    def push(self, text: str) -> None:
        if self.maxlen <= 0:
            return
        if len(self._dq) >= self.maxlen:
            self._dq.popleft()
        self._dq.append(text)

    def contains_recent(self, text: str, window: int) -> bool:
        if window <= 0:
            return False
        if not self._dq:
            return False
        # sprawdzamy ostatnie 'window' wpisów (od końca)
        tail = list(self._dq)[-window:]
        return text in tail


@dataclass
class CommentaryComposer:
    """
    Kompozytor komentarzy z globalnym cooldownem.

    Owijka na CommentsRepoMVP: wielokrotnie próbuje pobrać frazę z danej
    kategorii tak, aby nie naruszyć globalnego cooldownu (np. 4 zdarzenia).
    Jeśli się nie uda – przyjmuje rezultat z ostatniej próby.
    """
    repo: any
    global_cooldown: int = 4
    recent: RecentCache = field(default_factory=lambda: RecentCache(maxlen=50))
    _uses: Dict[str, int] = field(default_factory=dict)

    def pick(self, key: str, **vars) -> str:
        # jeśli brak repo lub pick się nie powiedzie – zwróć pusty string
        if not self.repo:
            return ""
        last_txt: Optional[str] = None
        # ogranicz liczbę prób, by uniknąć pętli
        for _ in range(6):
            try:
                txt = self.repo.pick(key, **vars) or ""
            except Exception:
                txt = ""
            if not txt:
                last_txt = ""
                break
            last_txt = txt
            # Gating semantyczny: mikro-frazy o wolnych tylko w fazie freekick
            phase = str(vars.get('phase', '') or '').lower()
            if key == 'announce' and phase != 'freekick':
                low = txt.lower()
                if ('rzut wolny' in low) or (' wolny' in low) or ('freekick' in low) or ('free kick' in low):
                    # spróbuj ponownie – wybierz neutralną frazę
                    continue
            if not self.recent.contains_recent(txt, self.global_cooldown):
                # OK – mogę użyć
                self.recent.push(txt)
                self._uses[txt] = self._uses.get(txt, 0) + 1
                return txt
            # w przeciwnym razie – jeszcze jedna próba
            continue
        # po próbach – użyj ostatniego
        if last_txt:
            self.recent.push(last_txt)
            self._uses[last_txt] = self._uses.get(last_txt, 0) + 1
            return last_txt
        return ""
