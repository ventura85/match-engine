from __future__ import annotations
"""
engine/substitutions.py

TODO: Odpowiada za zasady zmian i wybór zawodników do zmiany.
API: maybe_substitution(engine, minute, team)
"""
from typing import Any


def maybe_substitution(engine: Any, minute: int, team: Any) -> None:
    # jeżeli nie ma ławki - pomiń
    if len(team.players) <= 11:
        return
    # wybierz "zmęczonego" (na razie losowo) i rezerwowego z ławki
    out_idx = engine._rng.randint(0, 10)
    bench_idx = engine._rng.randint(11, len(team.players) - 1)
    out_p = team.players[out_idx]
    in_p = team.players[bench_idx]
    team.players[out_idx], team.players[bench_idx] = in_p, out_p
    engine._add_event(minute, "substitution", f"{minute}' - Zmiana w {team.name}: {out_p.name} -> {in_p.name}")
    engine.substitutions.append({'minute': minute, 'team': team.name, 'out': out_p.name, 'in': in_p.name})

