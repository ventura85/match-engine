from __future__ import annotations
import csv
import sys
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.match import MatchEngine
from engine.utils import set_random_seed
from models.team import Team
from models.player import Player
import json


DATA_DIR = ROOT / "data"
TEAMS_JSON = DATA_DIR / "teams.json"


def load_base_teams() -> Dict[str, Team]:
    data = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    teams: Dict[str, Team] = {}
    for t in data.get("teams", []):
        name = t.get("name", "Unknown Team")
        formation = t.get("formation", "4-4-2")
        style = t.get("style", "balanced")
        channel = t.get("attack_channel", "center")
        pressing = t.get("pressing", "normal")
        width = t.get("width", "normal")
        players: List[Player] = []
        for p in t.get("players", []):
            players.append(
                Player(
                    id=p.get("id", 0),
                    name=p.get("name", "Anon"),
                    position=p.get("position", "MID"),
                    attributes=p.get("attributes", {"physical": {}, "technical": {}, "mental": {}}),
                    energy=p.get("energy", 1.0),
                    form=p.get("form", 1.0),
                    traits=p.get("traits", []),
                )
            )
        teams[name] = Team(
            name=name,
            players=players,
            formation=formation,
            style=style,
            attack_channel=channel,
            pressing=pressing,
            width=width,
        )
    return teams


PRESETS = [
    {"name": "Balanced-4231", "style": "balanced", "channel": "center", "pressing": "normal", "width": "normal"},
    {"name": "MidBlock-4141-Narrow", "style": "balanced", "channel": "center", "pressing": "normal", "width": "narrow"},
    {"name": "CentralOverload-4141", "style": "balanced", "channel": "center", "pressing": "normal", "width": "narrow"},
    {"name": "WingOverload-4231-Wide", "style": "balanced", "channel": "wings", "pressing": "normal", "width": "wide"},
    {"name": "HighPress-433-Wide", "style": "attacking", "channel": "wings", "pressing": "high", "width": "wide"},
    {"name": "DirectPlay-442", "style": "attacking", "channel": "center", "pressing": "high", "width": "normal"},
    {"name": "LowBlock-442-Narrow", "style": "defensive", "channel": "center", "pressing": "low", "width": "narrow"},
    {"name": "ParkBreak-541-Wide", "style": "defensive", "channel": "wings", "pressing": "low", "width": "wide"},
]


def apply_preset(base: Team, preset: Dict[str, str]) -> Team:
    return Team(
        name=base.name,
        players=list(base.players),
        formation=base.formation,
        style=preset["style"],
        attack_channel=preset["channel"],
        pressing=preset["pressing"],
        width=preset["width"],
    )


def simulate_pair(A_base: Team, B_base: Team, a_preset: Dict[str, str], b_preset: Dict[str, str], games: int = 100) -> Dict:
    A = apply_preset(A_base, a_preset)
    B = apply_preset(B_base, b_preset)
    res = {
        "a_name": a_preset["name"],
        "b_name": b_preset["name"],
        "games": games,
        "win_a": 0,
        "win_b": 0,
        "draw": 0,
        "goals_a": 0,
        "goals_b": 0,
        "shots_a": 0,
        "shots_b": 0,
        "fouls_a": 0,
        "fouls_b": 0,
    }
    for i in range(games):
        set_random_seed(i)
        eng = MatchEngine(A, B, verbose=False, real_time=False)
        r = eng.simulate_match()
        sa, sb = r["score"]
        res["goals_a"] += sa
        res["goals_b"] += sb
        if sa > sb:
            res["win_a"] += 1
        elif sb > sa:
            res["win_b"] += 1
        else:
            res["draw"] += 1
        res["shots_a"] += r["shots"][A.name]
        res["shots_b"] += r["shots"][B.name]
        res["fouls_a"] += r["stats"]["fouls_a"]
        res["fouls_b"] += r["stats"]["fouls_b"]
    return res


def main() -> None:
    teams = load_base_teams()
    names = list(teams.keys())
    if len(names) < 2:
        print("Need at least two teams in data/teams.json")
        sys.exit(1)
    A_base = teams[names[0]]
    B_base = teams[names[1]]

    rows: List[Dict] = []
    for a in PRESETS:
        for b in PRESETS:
            rows.append(simulate_pair(A_base, B_base, a, b, games=50))

    out = ROOT / "reports" / "matrix.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote matrix to {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()

