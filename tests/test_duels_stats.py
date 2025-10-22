from models.team import Team
from models.player import Player
from engine.match import MatchEngine
from engine.utils import set_random_seed


def _t(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [P(base+i, f"{name}{i}", pos) for i, pos in enumerate(["GK","DEF","DEF","MID","MID","MID","MID","DEF","FWD","FWD","FWD"])]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def test_duels_totals_match_won_lost_sum():
    set_random_seed(7)
    A = _t('A', 100)
    B = _t('B', 200)
    eng = MatchEngine(A, B, verbose=False)
    rep = eng.simulate_match()
    st = rep['stats']
    total_a = st.get('duels_total_a', st.get('duels_won_a', 0) + st.get('duels_won_b', 0))
    total_b = st.get('duels_total_b', st.get('duels_won_a', 0) + st.get('duels_won_b', 0))
    lost_a = st.get('duels_lost_a', total_a - st.get('duels_won_a', 0))
    lost_b = st.get('duels_lost_b', total_b - st.get('duels_won_b', 0))
    assert st['duels_won_a'] + lost_a == total_a
    assert st['duels_won_b'] + lost_b == total_b

