from __future__ import annotations
"""
engine/eventlog.py

TODO: Prosty interfejs logowania zdarzeń do wewnętrznej listy silnika i ew. stdout.
API: add_event(engine, minute, kind, text)
"""
from typing import Any


def add_event(engine: Any, minute: int, kind: str, text: str) -> None:
    if not hasattr(engine, '_events'):
        return
    engine._events.append({"kind": kind, "text": text, "minute": int(minute)})
    if getattr(engine, 'verbose', False):
        try:
            print(text)
        except Exception:
            pass

