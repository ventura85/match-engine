from __future__ import annotations
from collections import Counter

from engine.match import MatchEngine
from engine.utils import set_random_seed
from models.player import Player
from models.team import Team


def _team(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(
            id=i,
            name=nm,
            position=pos,
            attributes={
                'physical': {'speed': 70, 'strength': 70, 'stamina': 80},
                'technical': {'passing': 70, 'shooting': 65, 'dribbling': 65, 'tackling': 70, 'marking': 70, 'reflexes': 60, 'handling': 60},
                'mental': {'positioning': 65, 'concentration': 65, 'decisions': 60, 'aggression': 50}
            },
            energy=1.0, form=1.0, traits=[]
        )
    players = [P(base+i, f"{name}{i}", pos) for i, pos in enumerate(["GK","DEF","DEF","MID","MID","MID","MID","DEF","FWD","FWD","FWD"])]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def test_goals_lists_match_scores():
    set_random_seed(101)
    A = _team('A', 10)
    B = _team('B', 100)
    eng = MatchEngine(A, B, verbose=False)
    rep = eng.simulate_match()
    goals = rep.get('goals') or []
    c = Counter(g['team'] for g in goals)
    assert rep['score_a'] == c.get(rep['team_a'], 0) == len(rep.get('goals_a') or [])
    assert rep['score_b'] == c.get(rep['team_b'], 0) == len(rep.get('goals_b') or [])


def test_corners_count_from_events():
    set_random_seed(202)
    A = _team('A', 20)
    B = _team('B', 200)
    eng = MatchEngine(A, B, verbose=False)
    rep = eng.simulate_match()
    events = rep.get('events_full') or rep['events']
    cnt_a = sum(1 for e in events if e['event_type'] == 'corner' and e.get('team') == rep['team_a'])
    cnt_b = sum(1 for e in events if e['event_type'] == 'corner' and e.get('team') == rep['team_b'])
    st = rep['stats']
    assert st['corners_a'] == cnt_a
    assert st['corners_b'] == cnt_b


def test_shots_on_target_events_not_exceed_stats():
    set_random_seed(303)
    A = _team('A', 30)
    B = _team('B', 300)
    eng = MatchEngine(A, B, verbose=False)
    rep = eng.simulate_match()
    events = rep.get('events_full') or rep['events']
    cnt_a = sum(1 for e in events if e['event_type'] == 'shot_on_target' and e.get('team') == rep['team_a'])
    cnt_b = sum(1 for e in events if e['event_type'] == 'shot_on_target' and e.get('team') == rep['team_b'])
    st = rep['stats']
    assert st['shots_on_target_a'] >= cnt_a
    assert st['shots_on_target_b'] >= cnt_b

