from models.player import Player
from models.team import Team
from engine.match import MatchEngine
from engine.utils import set_random_seed


def _team(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [
        P(base+0,f"{name} GK","GK"), P(base+1,f"{name} DEF1","DEF"), P(base+2,f"{name} DEF2","DEF"),
        P(base+3,f"{name} DEF3","DEF"), P(base+4,f"{name} MID1","MID"), P(base+5,f"{name} MID2","MID"),
        P(base+6,f"{name} MID3","MID"), P(base+7,f"{name} MID4","MID"), P(base+8,f"{name} FWD1","FWD"),
        P(base+9,f"{name} FWD2","FWD"), P(base+10,f"{name} FWD3","FWD"),
    ]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def test_top3_distances_not_identical():
    set_random_seed(123)
    A = _team('Red', 10)
    B = _team('Blue', 110)
    eng = MatchEngine(A, B, verbose=False)
    eng.simulate_match()
    # Odczytuj dystans bezpośrednio z obiektów graczy (dokładniejszy niż snapshot w raporcie)
    plist = getattr(eng, 'team_a').players
    top = sorted(plist, key=lambda p: getattr(p, 'distance_km', 0.0), reverse=True)[:3]
    vals = [round(getattr(p, 'distance_km', 0.0), 3) for p in top]
    # At least two values differ
    assert len(set(vals)) >= 2
