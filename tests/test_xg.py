from engine.match import MatchEngine
from engine.utils import set_random_seed
from models.team import Team
from models.player import Player


def _team(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [P(base+i, f"{name}{i}", pos) for i, pos in enumerate(["GK","DEF","DEF","MID","MID","MID","MID","DEF","FWD","FWD","FWD"])]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def test_xg_fields_present_and_reasonable():
    A = _team('A', 1000)
    B = _team('B', 2000)
    vals = []
    for sd in range(1, 31):  # kilkanaście losowych meczów dla stabilności
        set_random_seed(sd)
        eng = MatchEngine(A, B, verbose=False, real_time=False)
        rep = eng.simulate_match()
        st = rep['stats']
        assert 'xg_a' in st and 'xg_b' in st
        vals.append((st['xg_a'], st['xg_b']))
    for xa, xb in vals:
        assert 0.0 <= xa <= 10.0
        assert 0.0 <= xb <= 10.0

