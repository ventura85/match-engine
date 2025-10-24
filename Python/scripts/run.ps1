param(
  [int]$Seed = 42,
  [switch]$Verbose
)

$env:PYTHONUTF8=1
Write-Host "Running match simulation (seed=$Seed)"
python - << 'PY'
import json, random
from pathlib import Path
from models.team import Team
from models.player import Player
from engine.match import MatchEngine
from engine.utils import set_random_seed

def make_simple_team(name, base_id):
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [
        P(base_id+0,f"{name} GK","GK"), P(base_id+1,f"{name} DEF1","DEF"), P(base_id+2,f"{name} DEF2","DEF"),
        P(base_id+3,f"{name} DEF3","DEF"), P(base_id+4,f"{name} MID1","MID"), P(base_id+5,f"{name} MID2","MID"),
        P(base_id+6,f"{name} MID3","MID"), P(base_id+7,f"{name} MID4","MID"), P(base_id+8,f"{name} FWD1","FWD"),
        P(base_id+9,f"{name} FWD2","FWD"), P(base_id+10,f"{name} FWD3","FWD"),
    ]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')

set_random_seed($Seed)
A = make_simple_team("Team A", 1)
B = make_simple_team("Team B", 101)
eng = MatchEngine(A, B, verbose=bool($Verbose))
rep = eng.simulate_match()
print(json.dumps(rep, ensure_ascii=False))
PY
