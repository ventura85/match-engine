from __future__ import annotations
import json
from pathlib import Path
from models.team import Team
from models.player import Player
from engine.match import MatchEngine
from engine.utils import set_random_seed
from engine.stats import export


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


def test_ndjson_seq_and_sim_min_monotonic():
    set_random_seed(42)
    A = _team('A', 1)
    B = _team('B', 101)
    eng = MatchEngine(A, B, verbose=False)
    rep = eng.simulate_match()
    out = export(eng, seed=42, out_dir='out')
    nd = Path(out['ndjson']).read_text(encoding='utf-8').strip().splitlines()
    prev_seq = 0
    prev_min = 0
    for line in nd:
        obj = json.loads(line)
        assert obj['seq'] > prev_seq
        assert obj['sim_min'] >= prev_min
        prev_seq = obj['seq']
        prev_min = obj['sim_min']

