"""Testy profilu sędziego – wpływ mnożników na żółte.

Porównujemy przypadek 'strict' vs 'lenient' przy identycznym przebiegu RNG.
"""
from __future__ import annotations
import pytest

from models.player import Player
from models.team import Team
from engine.match import MatchEngine


def _pl(pid: int, name: str, pos: str) -> Player:
    return Player(
        id=pid, name=name, position=pos,
        attributes={
            'physical': {'speed': 70, 'strength': 70, 'stamina': 80},
            'technical': {'passing': 70, 'shooting': 65, 'dribbling': 65, 'tackling': 70, 'marking': 70, 'reflexes': 60, 'handling': 60},
            'mental': {'positioning': 65, 'concentration': 65, 'decisions': 60, 'aggression': 50},
        },
        energy=1.0, form=1.0, traits=[]
    )


def _teams() -> tuple[Team, Team]:
    A = Team(name='A', players=[
        _pl(1,'A GK','GK'), _pl(2,'A DEF','DEF'), _pl(3,'A MID','MID'), _pl(4,'A FWD','FWD'),
        _pl(5,'A P5','MID'), _pl(6,'A P6','MID'), _pl(7,'A P7','MID'), _pl(8,'A P8','DEF'), _pl(9,'A P9','FWD'), _pl(10,'A P10','FWD'), _pl(11,'A P11','FWD'),
    ])
    B = Team(name='B', players=[
        _pl(100,'B GK','GK'), _pl(101,'B DEF','DEF'), _pl(102,'B DEF2','DEF'), _pl(103,'B MID','MID'), _pl(104,'B MID2','MID'),
        _pl(105,'B MID3','MID'), _pl(106,'B MID4','MID'), _pl(107,'B DEF3','DEF'), _pl(108,'B FWD','FWD'), _pl(109,'B FWD2','FWD'), _pl(110,'B FWD3','FWD'),
    ])
    return A, B


def test_referee_strict_vs_lenient_changes_yellow_probability(monkeypatch: pytest.MonkeyPatch):
    A, B = _teams()

    # Wymuś faul w 1'
    def fake_minute(self: MatchEngine, half: int, minute: int) -> None:
        if minute == 1:
            self._simulate_foul(half, minute, self.team_a)

    monkeypatch.setattr(MatchEngine, "_simulate_minute", fake_minute, raising=True)

    # RNG kolejność: foul_place_box, direct_red, yellow
    calls = {'n': 0}
    def rng_seq():
        calls['n'] += 1
        if calls['n'] == 3:
            return 0.26  # graniczne dla p_yellow
        return 0.9

    import random
    monkeypatch.setattr(random, 'random', rng_seq, raising=False)

    # Lenient – p_yellow * 0.90 → poniżej 0.26 (raczej brak żółtej)
    # Ustabilizuj wybór karanego obrońcy, aby nie zjadać dodatkowych RNG
    monkeypatch.setattr(MatchEngine, "_pick_defender", lambda self, t: t.players[1], raising=True)
    eng_len = MatchEngine(A, B, verbose=False, referee_profile='lenient')
    rep_len = eng_len.simulate_match()

    # Reset RNG sekwencji dla drugiego meczu (oddzielny przebieg)
    calls['n'] = 0
    def rng_seq2():
        calls['n'] += 1
        if calls['n'] == 3:
            return 0.26
        return 0.9
    monkeypatch.setattr(random, 'random', rng_seq2, raising=False)

    # Strict – p_yellow * 1.15 → powyżej 0.26 (powinna być żółta)
    eng_str = MatchEngine(A, B, verbose=False, referee_profile='strict')
    rep_str = eng_str.simulate_match()

    assert rep_len['stats']['yellows_b'] == 0
    assert rep_str['stats']['yellows_b'] >= 1
