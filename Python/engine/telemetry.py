from __future__ import annotations
from typing import Any, Dict
from pathlib import Path
import json, time


def collect_distribution_snapshot(report: Dict[str, Any]) -> Dict[str, Any]:
    shots_a = report.get('shots', {}).get(report.get('team_a',''), 0)
    shots_b = report.get('shots', {}).get(report.get('team_b',''), 0)
    goals_a = report.get('score', (0,0))[0]
    goals_b = report.get('score', (0,0))[1]
    yellows = report.get('stats', {}).get('yellows_a', 0) + report.get('stats', {}).get('yellows_b', 0)
    return {
        'shots_per_match': shots_a + shots_b,
        'goals_per_match': goals_a + goals_b,
        'yellows_per_match': yellows,
    }


def write_snapshot(snapshot: Dict[str, Any], out_dir: str = 'out') -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    path = Path(out_dir) / f"distribution_{ts}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return str(path)

