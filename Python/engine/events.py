from __future__ import annotations
from typing import Dict, List, Optional, Any
import re


class EventBus:
    """
    Prosty bufor zdarzeń do warstwy komentarza.
    - Zdarzenia przechowujemy jako dict: {"kind": str, "text": str, "minute": int}
    - Jeśli minuta nie jest jawnie podana, spróbujemy ją wyekstrahować ze stringa
      w formacie "NN' - ..."; jeśli się nie uda, ustawiamy 1.
    """

    _re_min = re.compile(r"^\s*(\d{1,3})'")

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []

    # ————— helpers —————

    def _extract_minute(self, text: str) -> int:
        """Szukaj prefiksu "67' - ..." i zwróć minutę; jak brak – 1."""
        if not isinstance(text, str):
            return 1
        m = self._re_min.match(text)
        if m:
            try:
                return max(0, int(m.group(1)))
            except Exception:
                return 1
        return 1

    def _push(self, kind: str, text: str, minute: Optional[int] = None) -> None:
        if minute is None:
            minute = self._extract_minute(text)
        self._events.append({"kind": kind, "text": text, "minute": int(minute)})

    # ————— public API używane przez match.py —————

    def add_event(self, kind: str, text: str, minute: Optional[int] = None) -> None:
        """Ogólny rejestrator zdarzenia."""
        self._push(kind, text, minute)

    def add_info(self, text: str, minute: Optional[int] = None) -> None:
        """Krótkie, neutralne wpisy do kroniki."""
        self._push("info", text, minute)

    def add_micro(self, text: str, minute: Optional[int] = None) -> None:
        """Mikro-komentarze taktyczne / tło."""
        self._push("micro", text, minute)

    def add_banner(self, kind: str, text: str) -> None:
        """
        Banery nagłówkowe (start meczu itp.). Minuta = 0 żeby były na górze.
        """
        self._push(kind, text, minute=0)

    def dump(self) -> List[Dict[str, Any]]:
        """Zwraca pełną listę zdarzeń (kolejność dodawania)."""
        return list(self._events)
