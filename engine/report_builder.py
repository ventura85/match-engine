from __future__ import annotations
"""
engine/report_builder.py

TODO: Składanie pełnego raportu końcowego z obiektu silnika.
API: build_report(engine) -> dict
"""
from typing import Any, Dict, List


def build_report(engine: Any) -> Dict:
    TOTAL_SIM_MINUTES = getattr(engine, 'TOTAL_SIM_MINUTES', 90)
    # pomocnicze: kompresja minut do 1..10
    def _compress_minute(m: int) -> int:
        if m < 1:
            return 1
        return min(10, int((m - 1) * 10 / TOTAL_SIM_MINUTES) + 1)

    timeline: List[Dict] = []
    for e in getattr(engine, '_events', []) or []:
        timeline.append({
            'minute': _compress_minute(int(e.get('minute', 1))),
            'team': '',
            'event_type': e.get('kind', 'info'),
            'description': e.get('text', ''),
        })

    score_a = len(engine.stats.goals_a)
    score_b = len(engine.stats.goals_b)
    goals_combined = (
        [{'team': engine.team_a.name, 'minute': m, 'scorer': s, 'assist': a} for (m, s, a) in engine.stats.goals_a]
        + [{'team': engine.team_b.name, 'minute': m, 'scorer': s, 'assist': a} for (m, s, a) in engine.stats.goals_b]
    )

    def build_player_stats(team) -> List[Dict]:
        out: List[Dict] = []
        for p in team.players:
            out.append({
                'id': getattr(p, 'id', 0),
                'name': getattr(p, 'name', ''),
                'position': getattr(p, 'position', ''),
                'energy': round(getattr(p, 'energy', 1.0), 3),
                'distance_km': round(float(getattr(p, 'distance_km', 0.0) or 0.0), 2),
            })
        return out

    pos_a = round(100 * engine.possession_a_ticks / max(1, engine.possession_a_ticks + engine.possession_b_ticks), 1)
    pos_b = round(100 - pos_a, 1)
    return {
        'team_a': engine.team_a.name,
        'team_b': engine.team_b.name,
        'score': (score_a, score_b),
        'score_a': score_a,
        'score_b': score_b,
        'referee': engine.referee,
        'possession': {engine.team_a.name: pos_a, engine.team_b.name: pos_b},
        'shots': {engine.team_a.name: engine.stats.shots_a, engine.team_b.name: engine.stats.shots_b},
        'shots_on_target': {engine.team_a.name: engine.stats.shots_on_a, engine.team_b.name: engine.stats.shots_on_b},
        'events': timeline,
        'events_full': timeline,
        'goals': goals_combined,
        'goals_a': [{'minute': m, 'scorer': s, 'assist': a} for (m, s, a) in engine.stats.goals_a],
        'goals_b': [{'minute': m, 'scorer': s, 'assist': a} for (m, s, a) in engine.stats.goals_b],
        'substitutions': list(getattr(engine, 'substitutions', []) or []),
        'tactical_impact': {'team_a_style': getattr(engine.team_a, 'style', 'balanced'), 'team_b_style': getattr(engine.team_b, 'style', 'balanced')},
        'stats': {
            'possession_a': pos_a, 'possession_b': pos_b,
            'shots_a': engine.stats.shots_a, 'shots_on_a': engine.stats.shots_on_a,
            'shots_b': engine.stats.shots_b, 'shots_on_b': engine.stats.shots_on_b,
            'xg_a': round(engine.stats.xg_a, 2), 'xg_b': round(engine.stats.xg_b, 2),
            'duels_won_a': engine.stats.duels_won_a, 'duels_won_b': engine.stats.duels_won_b,
            'duels_total_a': engine.stats.duels_total_a, 'duels_total_b': engine.stats.duels_total_b,
            'fouls_a': engine.stats.fouls_a, 'fouls_b': engine.stats.fouls_b,
            'yellows_a': engine.stats.yellows_a, 'yellows_b': engine.stats.yellows_b,
            'reds_a': engine.stats.reds_a, 'reds_b': engine.stats.reds_b,
            'corners_a': engine.stats.corners_a, 'corners_b': engine.stats.corners_b,
            'freekicks_a': engine.stats.freekicks_a, 'freekicks_b': engine.stats.freekicks_b,
            'penalties_a': engine.stats.penalties_a, 'penalties_b': engine.stats.penalties_b,
        },
        'xg_a': round(engine.stats.xg_a, 2),
        'xg_b': round(engine.stats.xg_b, 2),
        'player_stats': {
            engine.team_a.name: build_player_stats(engine.team_a),
            engine.team_b.name: build_player_stats(engine.team_b),
        },
    }

