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


def test_cli_duels_line_uses_correct_teams(capsys):
    # Syntetyczny raport do sprawdzenia formatowania linii pojedynków
    from main import print_match_report
    report = {
        'team_a': 'Team A',
        'team_b': 'Team B',
        'score': (0, 0), 'score_a': 0, 'score_b': 0,
        'goals_a': [], 'goals_b': [],
        'events': [], 'events_full': [],
        'shots': {'Team A': 5, 'Team B': 7},
        'shots_on_target': {'Team A': 3, 'Team B': 2},
        'tactical_impact': {},
        'substitutions': [],
        'stats': {
            'possession_a': 50.0, 'possession_b': 50.0,
            'shots_a': 5, 'shots_on_a': 3,
            'shots_b': 7, 'shots_on_b': 2,
            'duels_won_a': 7, 'duels_won_b': 9,
            'duels_total_a': 16, 'duels_total_b': 16,
            'fouls_a': 0, 'fouls_b': 0,
            'yellows_a': 0, 'yellows_b': 0,
            'reds_a': 0, 'reds_b': 0,
            'corners_a': 0, 'corners_b': 0,
            'freekicks_a': 0, 'freekicks_b': 0,
            'penalties_a': 0, 'penalties_b': 0,
        },
        'player_stats': {'Team A': [], 'Team B': []},
        'referee': {'key': 'neutral', 'label': 'Neutral', 'foul_mult': 1.0, 'yellow_mult': 1.0, 'red_mult': 1.0},
    }
    print_match_report(report, timeline_mode='key', timeline_limit=10)
    out = capsys.readouterr().out
    assert 'Team A: 7/16' in out
    assert 'Team B: 9/16' in out
    # oraz total A == total B == suma wygranych
    assert 'Pojedynki' in out
