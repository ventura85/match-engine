from __future__ import annotations

from models.team import Team
from models.player import Player
from engine.match import MatchEngine
from engine.utils import set_random_seed


def _team(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [P(base+i, f"{name}{i}", pos) for i, pos in enumerate(["GK","DEF","DEF","MID","MID","MID","MID","DEF","FWD","FWD","FWD"])]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def _simulate_seed(seed: int):
    set_random_seed(seed)
    A = _team('A', 1000 + seed)
    B = _team('B', 2000 + seed)
    eng = MatchEngine(A, B, verbose=False, real_time=False)
    return eng.simulate_match()


def test_freekicks_count_awards_only():
    rep = _simulate_seed(7)
    ta, tb = rep['team_a'], rep['team_b']
    events = rep.get('events_full') or rep['events']
    fa = sum(1 for e in events if e.get('event_type') == 'freekick_awarded' and e.get('team') == ta)
    fb = sum(1 for e in events if e.get('event_type') == 'freekick_awarded' and e.get('team') == tb)
    st = rep['stats']
    assert st['freekicks_a'] == fa
    assert st['freekicks_b'] == fb


def test_micro_freekick_phrases_do_not_increase_stats():
    rep = _simulate_seed(11)
    events = rep.get('events_full') or rep['events']
    st = rep['stats']
    fa = sum(1 for e in events if e.get('event_type') == 'freekick_awarded' and e.get('team') == rep['team_a'])
    fb = sum(1 for e in events if e.get('event_type') == 'freekick_awarded' and e.get('team') == rep['team_b'])
    assert st['freekicks_a'] == fa and st['freekicks_b'] == fb


def test_goals_shots_invariants():
    rep = _simulate_seed(42)
    st = rep['stats']
    assert rep['score_a'] <= st['shots_on_target_a'] <= st['shots_a']
    assert rep['score_b'] <= st['shots_on_target_b'] <= st['shots_b']
