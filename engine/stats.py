# engine/stats.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class TeamStats:
    # Strzały
    shots: int = 0
    shots_on_target: int = 0
    goals: int = 0

    # Stałe fragmenty
    corners_for: int = 0
    free_kicks_for: int = 0
    penalties_for: int = 0

    # Pojedynki
    duels_won: int = 0
    duels_lost: int = 0
    duels_total: int = 0  # NOWE: łączna liczba pojedynków (czytelność raportu)

    # Dyscyplina
    fouls: int = 0
    cards_yellow: int = 0
    cards_red: int = 0

    # Wejścia w tercję/box (opcjonalne)
    final_third_entries: int = 0
    box_entries: int = 0

    # Energia/wytrzymałość (opcjonalnie)
    avg_energy_end: float = 0.0

    # xG (prosty agregat, jeśli liczysz)
    xg: float = 0.0

def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchStats:
    """
    Zbiorcze statystyki meczu. Bezpieczne domyślne — jeśli engine
    czegoś nie używa, pozostanie 0.
    """
    team_a_name: str = "Team A"
    team_b_name: str = "Team B"

    team_a: TeamStats = field(default_factory=TeamStats)
    team_b: TeamStats = field(default_factory=TeamStats)

    # Posiadanie (jeśli liczysz w runtime; inaczej policzysz ex post)
    possession_a_pct: float = 0.0
    possession_b_pct: float = 0.0

    # Czas (opcjonalnie)
    stoppage_time_added: int = 0

    # Zapas: legacy pola widziane w niektórych implementacjach
    # (zostawione, żeby nie łamać importów/odwołań)
    duels_won_a: int = 0      # legacy alias → mapujemy do team_a.duels_won
    duels_won_b: int = 0      # legacy alias → mapujemy do team_b.duels_won
    duels_total_a: int = 0    # NOWE: alias zgodny z poprzednimi logami
    duels_total_b: int = 0    # NOWE: alias zgodny z poprzednimi logami

    def inc_duel_for_attacking_team(self, is_team_a: bool, won: bool | None = None) -> None:
        """
        Zwiększ licznik pojedynków po stronie atakującej drużyny.
        - duels_total zawsze +1
        - jeśli won==True → duels_won+1 po stronie atakującego
        - jeśli won==False → duels_lost+1 po stronie atakującego
        """
        team = self.team_a if is_team_a else self.team_b
        team.duels_total += 1
        if is_team_a:
            self.duels_total_a += 1
        else:
            self.duels_total_b += 1

        if won is True:
            team.duels_won += 1
            if is_team_a:
                self.duels_won_a += 1
            else:
                self.duels_won_b += 1
        elif won is False:
            team.duels_lost += 1

    def to_report_block(self) -> Dict[str, Any]:
        """
        Zwraca słownik wygodny do wpięcia w raport końcowy.
        """
        return {
            "possession": {
                self.team_a_name: round(self.possession_a_pct, 1),
                self.team_b_name: round(self.possession_b_pct, 1),
            },
            "shots": {
                self.team_a_name: {
                    "total": self.team_a.shots,
                    "on_target": self.team_a.shots_on_target,
                    "goals": self.team_a.goals,
                },
                self.team_b_name: {
                    "total": self.team_b.shots,
                    "on_target": self.team_b.shots_on_target,
                    "goals": self.team_b.goals,
                },
            },
            "duels": {
                self.team_a_name: {
                    "won": self.team_a.duels_won,
                    "lost": self.team_a.duels_lost,
                    "total": self.team_a.duels_total,
                },
                self.team_b_name: {
                    "won": self.team_b.duels_won,
                    "lost": self.team_b.duels_lost,
                    "total": self.team_b.duels_total,
                },
            },
            "set_pieces": {
                self.team_a_name: {
                    "corners": self.team_a.corners_for,
                    "free_kicks": self.team_a.free_kicks_for,
                    "penalties": self.team_a.penalties_for,
                },
                self.team_b_name: {
                    "corners": self.team_b.corners_for,
                    "free_kicks": self.team_b.free_kicks_for,
                    "penalties": self.team_b.penalties_for,
                },
            },
            "discipline": {
                self.team_a_name: {
                    "fouls": self.team_a.fouls,
                    "yellow": self.team_a.cards_yellow,
                    "red": self.team_a.cards_red,
                },
                self.team_b_name: {
                    "fouls": self.team_b.fouls,
                    "yellow": self.team_b.cards_yellow,
                    "red": self.team_b.cards_red,
                },
            },
            "xg": {
                self.team_a_name: round(self.team_a.xg, 3),
                self.team_b_name: round(self.team_b.xg, 3),
            },
            "stoppage_time_added": self.stoppage_time_added,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Pełny zrzut statystyk (w tym obiekty team_a/team_b).
        """
        d = asdict(self)
        # Zachowaj spójność aliasów legacy
        d["team_a"]["duels_total"] = self.team_a.duels_total
        d["team_b"]["duels_total"] = self.team_b.duels_total
        return d


def _collect_events(engine: Any) -> list[dict]:
    evs: list[dict] = []
    try:
        raw = getattr(engine, "_events", None)
        if isinstance(raw, list):
            for e in raw:
                if isinstance(e, dict):
                    evs.append({
                        "minute": int(e.get("minute", 1) or 1),
                        "type": e.get("kind", e.get("type", "info")),
                        "text": e.get("text", ""),
                    })
    except Exception:
        pass
    return evs


def export(engine: Any, seed: int | None = None, out_dir: str = "out") -> dict[str, str]:
    from pathlib import Path
    import json
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sid = str(seed) if seed is not None else 'na'

    # NDJSON
    ndjson_path = out / f"match_{sid}.ndjson"
    events = _collect_events(engine)
    with ndjson_path.open('w', encoding='utf-8') as f:
        for i, e in enumerate(events, start=1):
            rec = {
                "seq": i,
                "sim_min": int(e.get("minute", 1) or 1),
                "rt_ms": None,
                "type": str(e.get("type", "info")),
                "team_id": None,
                "actors": [],
                "payload": {"text": e.get("text", "")},
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # STATS JSON (skrót)
    stats_path = out / f"stats_{sid}.json"
    data = {
        "team_a": getattr(getattr(engine, 'team_a', None), 'name', 'A'),
        "team_b": getattr(getattr(engine, 'team_b', None), 'name', 'B'),
        "shots_a": getattr(getattr(engine, 'stats', None), 'shots_a', 0),
        "shots_b": getattr(getattr(engine, 'stats', None), 'shots_b', 0),
        "yellows_a": getattr(getattr(engine, 'stats', None), 'yellows_a', 0),
        "yellows_b": getattr(getattr(engine, 'stats', None), 'yellows_b', 0),
        "goals_a": len(getattr(getattr(engine, 'stats', None), 'goals_a', []) or []),
        "goals_b": len(getattr(getattr(engine, 'stats', None), 'goals_b', []) or []),
    }
    with stats_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"ndjson": str(ndjson_path), "stats": str(stats_path)}
