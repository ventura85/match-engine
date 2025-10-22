"""Testy wpływu agresji i decyzji na kartki/faule.

Uwaga: testy wymuszają faul w konkretnej minucie oraz kontrolują RNG,
aby porównać scenariusze high-aggression vs low-aggression.
"""
from __future__ import annotations
import types
import pytest

from models.player import Player
from models.team import Team
from engine.match import MatchEngine


def _pl(pid: int, name: str, pos: str, *, aggr: int = 50, decis: int = 60) -> Player:
    return Player(
        id=pid,
        name=name,
        position=pos,
        attributes={
            'physical': {'speed': 70, 'strength': 70, 'stamina': 80},
            'technical': {'passing': 70, 'shooting': 65, 'dribbling': 65, 'tackling': 70, 'marking': 70, 'reflexes': 60, 'handling': 60},
            'mental': {'positioning': 65, 'concentration': 65, 'decisions': decis, 'aggression': aggr},
        },
        energy=1.0,
        form=1.0,
        traits=[],
    )


def _teams_with_def(def_aggr: int, def_decis: int) -> tuple[Team, Team, Player]:
    # A atakuje, B broni – kontrolujemy jednego obrońcę B
    A = Team(name='A', players=[
        _pl(1,'A GK','GK'), _pl(2,'A DEF','DEF'), _pl(3,'A MID','MID'), _pl(4,'A FWD','FWD'),
        _pl(5,'A P5','MID'), _pl(6,'A P6','MID'), _pl(7,'A P7','MID'), _pl(8,'A P8','DEF'), _pl(9,'A P9','FWD'), _pl(10,'A P10','FWD'), _pl(11,'A P11','FWD'),
    ])
    defB = _pl(101,'B DEF KEY','DEF', aggr=def_aggr, decis=def_decis)
    B = Team(name='B', players=[
        _pl(100,'B GK','GK'), defB, _pl(102,'B DEF2','DEF'), _pl(103,'B MID','MID'), _pl(104,'B MID2','MID'),
        _pl(105,'B MID3','MID'), _pl(106,'B MID4','MID'), _pl(107,'B DEF3','DEF'), _pl(108,'B FWD','FWD'), _pl(109,'B FWD2','FWD'), _pl(110,'B FWD3','FWD'),
    ])
    return A, B, defB


def test_aggression_affects_yellow_probability(monkeypatch: pytest.MonkeyPatch):
    # High aggression defender vs low aggression defender
    A_h, B_h, def_high = _teams_with_def(90, 40)
    A_l, B_l, def_low  = _teams_with_def(10, 90)

    # Wymuś faul i wyłącz bezpośrednie czerwone
    def fake_minute(self: MatchEngine, half: int, minute: int) -> None:
        if minute == 1:
            self._simulate_foul(half, minute, self.team_a)

    monkeypatch.setattr(MatchEngine, "_simulate_minute", fake_minute, raising=True)

    import engine.match as em
    monkeypatch.setattr(em, "DIRECT_RED_PROB", 0.0, raising=False)
    monkeypatch.setattr(em, "SECOND_YELLOW_TO_RED_PROB", 0.0, raising=False)

    # RNG tak, by yellow zaszedł tylko przy wyższym p_yellow
    calls = {'n': 0}
    def rng_yellow():
        # pierwsze wywołanie w _simulate_foul: foul_place_box – nieistotne
        # drugie: direct red (zablokowane przez 0.0)
        # trzecie: yellow check – zwracamy 0.20
        calls['n'] += 1
        if calls['n'] == 3:
            return 0.20
        return 0.9

    import random
    monkeypatch.setattr(random, 'random', rng_yellow, raising=False)

    e_high = MatchEngine(A_h, B_h, verbose=False, real_time=False)
    rep_h = e_high.simulate_match()
    e_low  = MatchEngine(A_l, B_l, verbose=False, real_time=False)
    rep_l = e_low.simulate_match()

    # Żółte powinny częściej występować dla wysokiej agresji
    assert rep_h['stats']['yellows_b'] >= 1
    assert rep_l['stats']['yellows_b'] == 0


def test_aggression_affects_direct_red_probability(monkeypatch: pytest.MonkeyPatch):
    A_h, B_h, def_high = _teams_with_def(90, 40)
    A_l, B_l, def_low  = _teams_with_def(10, 90)

    def fake_minute(self: MatchEngine, half: int, minute: int) -> None:
        if minute == 1:
            self._simulate_foul(half, minute, self.team_a)

    monkeypatch.setattr(MatchEngine, "_simulate_minute", fake_minute, raising=True)

    import engine.match as em
    monkeypatch.setattr(em, "YELLOW_PROB", 0.0, raising=False)

    # RNG: direct red check → 0.025, reszta 0.9
    calls = {'n': 0}
    def rng_red():
        calls['n'] += 1
        if calls['n'] == 2:
            return 0.025
        return 0.9

    import random
    monkeypatch.setattr(random, 'random', rng_red, raising=False)

    e_high = MatchEngine(A_h, B_h, verbose=False, real_time=False)
    rep_h = e_high.simulate_match()
    e_low  = MatchEngine(A_l, B_l, verbose=False, real_time=False)
    rep_l = e_low.simulate_match()

    assert rep_h['stats']['reds_b'] >= 1
    assert rep_l['stats']['reds_b'] == 0

