from __future__ import annotations
import math
from models.player import Player
from models.team import Team
from engine.fatigue import apply_fatigue_tick, FatigueContext, effective_skill


def _make_team_with_player(p: Player) -> Team:
    return Team(name=f"T_{p.name}", players=[p], formation="4-4-2", style='balanced', attack_channel='center')


def test_work_rate_affects_energy_drop_over_90_minutes():
    p_low = Player(id=1, name='LowWR', position='MID', attributes={'physical':{'stamina':80}, 'technical':{}, 'mental':{}}, energy=1.0, work_rate='low')
    p_high = Player(id=2, name='HighWR', position='MID', attributes={'physical':{'stamina':80}, 'technical':{}, 'mental':{}}, energy=1.0, work_rate='high')
    t_low = _make_team_with_player(p_low)
    t_high = _make_team_with_player(p_high)

    for minute in range(1, 91):
        ctx_low = FatigueContext(minute=minute, team_in_possession=t_low, defending_team=t_high)
        apply_fatigue_tick([p_low], [p_high], ctx_low)

    e_low_100 = p_low.energy * 100.0
    e_high_100 = p_high.energy * 100.0
    # Low work rate should retain more energy than high work rate
    assert e_low_100 - e_high_100 > 0.5


def test_effective_skill_reduces_with_low_energy():
    p = Player(id=3, name='Test', position='MID', attributes={'physical':{}, 'technical':{}, 'mental':{}}, energy=0.8)
    base = 70.0
    high = effective_skill(p, base)
    p.energy = 0.25
    low = effective_skill(p, base)
    assert low < high

