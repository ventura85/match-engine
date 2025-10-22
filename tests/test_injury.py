from __future__ import annotations
import random
from models.player import Player
from models.team import Team
from engine.injury import maybe_injury
from engine.match import MatchEngine


def _player(name: str, energy: float = 1.0) -> Player:
    return Player(id=random.randint(1,9999), name=name, position='MID', attributes={'physical':{'stamina':80}, 'technical':{}, 'mental':{}}, energy=energy)


def test_more_injuries_when_energy_low_and_high_pressing_strict_ref():
    random.seed(123)
    p_low = _player('L', energy=0.20)
    p_high = _player('H', energy=0.80)
    teamA = Team(name='A', players=[p_low])
    teamB = Team(name='B', players=[p_high])

    def count_inj(p, strict, opp_high):
        c = 0
        for m in range(1, 101):
            if maybe_injury(p, m, teamA, strict_ref=strict, opponent_high_press=opp_high):
                c += 1
        return c

    c_low = count_inj(p_low, strict=True, opp_high=True)
    c_high = count_inj(p_high, strict=False, opp_high=False)
    assert c_low > c_high


def test_requires_sub_reduces_slots(monkeypatch):
    # Create teams with bench
    def mk_team(name: str, base: int) -> Team:
        ps = [Player(id=base+i, name=f"{name}{i}", position=('GK' if i==0 else 'MID'), attributes={'physical':{'stamina':80}, 'technical':{}, 'mental':{}}, energy=1.0) for i in range(14)]
        return Team(name=name, players=ps)
    A = mk_team('A', 100)
    B = mk_team('B', 200)
    # Force injuries always and requires_sub always
    import engine.injury as inj
    monkeypatch.setattr(inj, '_base_prob', lambda ctx: 1.0, raising=True)
    monkeypatch.setattr(inj, 'get_config', lambda : type('X', (), {'get': staticmethod(lambda *a, **k: {'minor':1.0,'moderate':1.0,'severe':1.0})})(), raising=False)
    eng = MatchEngine(A, B, verbose=False, real_time=False)
    subs_before_a = eng._subs_left[A.name]
    # Simulate one minute to trigger injuries and forced subs
    eng._simulate_minute(half=1, minute=1)
    subs_after_a = eng._subs_left[A.name]
    assert subs_after_a < subs_before_a

