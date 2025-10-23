from __future__ import annotations
import json
from pathlib import Path

from models.player import Player
from models.team import Team
from main import render_lineups, _migrate_stats_keys, print_match_report


def _mk_team_with_positions(name: str, overall_physical: int = 100) -> Team:
    # Zawodnik z przewidywalnym overall ~90.0
    p_gk = Player(id=1, name=f"{name} GK", position="GK", attributes={
        'physical': {'speed': overall_physical},
        'technical': {}, 'mental': {}
    }, energy=1.0, form=1.0)
    p_def = Player(id=2, name=f"{name} DEF", position="DEF", attributes={'physical': {'speed': 50}}, energy=1.0, form=1.0)
    p_mid = Player(id=3, name=f"{name} MID", position="MID", attributes={'physical': {'speed': 50}}, energy=1.0, form=1.0)
    p_fwd = Player(id=4, name=f"{name} FWD", position="FWD", attributes={'physical': {'speed': 50}}, energy=1.0, form=1.0)
    return Team(name=name, players=[p_gk, p_def, p_mid, p_fwd], formation="4-4-2", style='balanced', attack_channel='center')


def test_cli_renders_player_overall_property(capsys):
    A = _mk_team_with_positions('A', overall_physical=100)
    B = _mk_team_with_positions('B', overall_physical=100)
    # Overall dla GK A ≈ 90.0 (patrz Player.get_overall_rating())
    render_lineups(A, B)
    out = capsys.readouterr().out
    assert "Overall: 90.0" in out


def test_migrates_shots_keys_to_shots_on_target():
    report = {
        'team_a': 'A', 'team_b': 'B',
        'score': (0, 0), 'score_a': 0, 'score_b': 0,
        'events': [], 'events_full': [],
        'stats': {
            'possession_a': 50.0, 'possession_b': 50.0,
            'shots_a': 5, 'shots_on_a': 3,
            'shots_b': 7, 'shots_on_b': 2,
            'duels_won_a': 0, 'duels_won_b': 0,
            'duels_total_a': 0, 'duels_total_b': 0,
            'fouls_a': 0, 'fouls_b': 0,
            'yellows_a': 0, 'yellows_b': 0,
            'reds_a': 0, 'reds_b': 0,
            'corners_a': 0, 'corners_b': 0,
            'freekicks_a': 0, 'freekicks_b': 0,
            'penalties_a': 0, 'penalties_b': 0,
        }
    }
    _migrate_stats_keys(report)
    st = report['stats']
    assert 'shots_on_a' not in st and 'shots_on_b' not in st
    assert st['shots_on_target_a'] == 3
    assert st['shots_on_target_b'] == 2
    # drukowanie nie powinno się wywalać
    # (nie aserty, tylko sanity run)
    print_match_report(report, timeline_mode='key', timeline_limit=5)

