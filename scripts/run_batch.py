from __future__ import annotations
import csv
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

from engine.match import MatchEngine
from engine.utils import set_random_seed
from models.team import Team
from models.player import Player

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TEAMS_JSON = DATA_DIR / "teams.json"


def load_teams() -> Dict[str, Team]:
    data = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    teams: Dict[str, Team] = {}
    for t in data.get("teams", []):
        name = t.get("name", "Unknown Team")
        formation = t.get("formation", "4-4-2")
        style = t.get("style", "balanced")
        attack_channel = t.get("attack_channel", "center")
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
        teams[name] = Team(name=name, players=players, formation=formation, style=style, attack_channel=attack_channel)
    return teams


def simulate_many(n: int = 200, team_a: str | None = None, team_b: str | None = None) -> List[Dict]:
    teams = load_teams()
    if team_a is None:
        team_a = list(teams.keys())[0]
    if team_b is None:
        team_b = next((k for k in teams.keys() if k != team_a), team_a)
    A, B = teams[team_a], teams[team_b]

    results: List[Dict] = []
    for seed in range(n):
        set_random_seed(seed)
        eng = MatchEngine(A, B, verbose=False, real_time=False)
        rep = eng.simulate_match()
        row = {
            "seed": seed,
            "score_a": rep["score"][0],
            "score_b": rep["score"][1],
            "shots_a": rep["shots"][A.name],
            "shots_b": rep["shots"][B.name],
            "on_a": rep["shots_on_target"][A.name],
            "on_b": rep["shots_on_target"][B.name],
            "pos_a": rep["possession"][A.name],
            "pos_b": rep["possession"][B.name],
            "corners_a": rep["stats"]["corners_a"],
            "corners_b": rep["stats"]["corners_b"],
            "fouls_a": rep["stats"]["fouls_a"],
            "fouls_b": rep["stats"]["fouls_b"],
            "yellows_a": rep["stats"]["yellows_a"],
            "yellows_b": rep["stats"]["yellows_b"],
        }
        results.append(row)
    return results


def write_csv(rows: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    data = simulate_many(n=200)
    out = Path(__file__).resolve().parents[1] / "reports" / "batch_stats.csv"
    write_csv(data, out)
    print(f"Wrote {len(data)} rows to {out}")

