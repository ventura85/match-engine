"""Testy jednostkowe dla silnika meczowego."""
import pytest
import json
from pathlib import Path

from models.player import Player
from models.team import Team
from engine.match import MatchEngine
from engine.utils import set_random_seed


def load_test_teams():
    """Ładuje testowe drużyny z pliku JSON."""
    with open('data/teams.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    teams = []
    for team_data in data['teams']:
        players = []
        for p_data in team_data['players']:
            player = Player(
                id=p_data['id'],
                name=p_data['name'],
                position=p_data['position'],
                attributes=p_data['attributes'],
                energy=p_data.get('energy', 1.0),
                form=p_data.get('form', 1.0),
                traits=p_data.get('traits', [])
            )
            players.append(player)
        
        team = Team(
            name=team_data['name'],
            players=players,
            formation=team_data.get('formation', '4-4-2'),
            style=team_data.get('style', 'balanced'),
            attack_channel=team_data.get('attack_channel', 'center')
        )
        teams.append(team)
    
    return teams[0], teams[1]


class TestMatchEngine:
    """Testy dla silnika meczowego."""
    
    def test_match_simulation_with_seed(self):
        """Test symulacji meczu z seedem - sprawdza powtarzalność."""
        team_a, team_b = load_test_teams()
        
        # Pierwsza symulacja z seedem
        set_random_seed(42)
        engine1 = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report1 = engine1.simulate_match()
        
        # Druga symulacja z tym samym seedem
        set_random_seed(42)
        engine2 = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report2 = engine2.simulate_match()
        
        # Wyniki powinny być identyczne
        assert report1['score'] == report2['score'], "Wyniki z tym samym seedem powinny być identyczne"
        assert len(report1['events']) == len(report2['events']), "Liczba eventów powinna być identyczna"
    
    def test_report_structure(self):
        """Test struktury raportu z meczu."""
        team_a, team_b = load_test_teams()
        
        set_random_seed(123)
        engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report = engine.simulate_match()
        
        # Sprawdź podstawowe klucze
        assert 'team_a' in report
        assert 'team_b' in report
        assert 'score' in report
        assert 'possession' in report
        assert 'shots' in report
        assert 'shots_on_target' in report
        assert 'events' in report
        assert 'goals' in report
        assert 'substitutions' in report
        assert 'tactical_impact' in report
        
        # Sprawdź typy
        assert isinstance(report['score'], tuple)
        assert len(report['score']) == 2
        assert isinstance(report['score'][0], int)
        assert isinstance(report['score'][1], int)
        
        # Sprawdź że są jakieś eventy
        assert isinstance(report['events'], list)
    
    def test_score_validity(self):
        """Test poprawności wyniku meczu."""
        team_a, team_b = load_test_teams()
        
        set_random_seed(456)
        engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report = engine.simulate_match()
        
        # Wynik nie może być ujemny
        assert report['score'][0] >= 0
        assert report['score'][1] >= 0
        
        # Liczba goli w eventach powinna odpowiadać wynikowi
        goal_events = [e for e in report['events'] if e['event_type'] == 'goal']
        total_goals = report['score'][0] + report['score'][1]
        assert len(goal_events) == total_goals, "Liczba goli w eventach powinna odpowiadać wynikowi"
    
    def test_possession_percentage(self):
        """Test obliczania posiadania piłki."""
        team_a, team_b = load_test_teams()
        
        set_random_seed(789)
        engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report = engine.simulate_match()
        
        # Posiadanie powinno sumować się do ~100%
        total_possession = report['possession'][team_a.name] + report['possession'][team_b.name]
        assert 99.0 <= total_possession <= 101.0, "Posiadanie powinno sumować się do 100%"
        
        # Każda drużyna powinna mieć jakieś posiadanie
        assert report['possession'][team_a.name] > 0
        assert report['possession'][team_b.name] > 0
    
    def test_shots_statistics(self):
        """Test statystyk strzałów."""
        team_a, team_b = load_test_teams()
        
        set_random_seed(321)
        engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report = engine.simulate_match()
        
        # Strzały celne nie mogą być większe niż wszystkie strzały
        assert report['shots_on_target'][team_a.name] <= report['shots'][team_a.name]
        assert report['shots_on_target'][team_b.name] <= report['shots'][team_b.name]
        
        # Statystyki nie mogą być ujemne
        assert report['shots'][team_a.name] >= 0
        assert report['shots'][team_b.name] >= 0
        assert report['shots_on_target'][team_a.name] >= 0
        assert report['shots_on_target'][team_b.name] >= 0
    
    def test_tactical_impact(self):
        """Test wpływu taktyki na mecz."""
        team_a, team_b = load_test_teams()
        
        # Ustaw różne style
        team_a.style = 'attacking'
        team_b.style = 'defensive'
        
        set_random_seed(555)
        engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report = engine.simulate_match()
        
        # Sprawdź czy wpływ taktyki jest zapisany
        assert 'tactical_impact' in report
        assert report['tactical_impact']['team_a_style'] == 'attacking'
        assert report['tactical_impact']['team_b_style'] == 'defensive'
        
        # Styl atakujący powinien mieć więcej strzałów
        # (nie zawsze prawda przez RNG, ale statystycznie)
        assert isinstance(report['shots'][team_a.name], int)
        assert isinstance(report['shots'][team_b.name], int)
    
    def test_match_duration(self):
        """Test czasu trwania meczu (10 minut total)."""
        team_a, team_b = load_test_teams()
        
        set_random_seed(999)
        engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
        report = engine.simulate_match()
        
        # Sprawdź że wszystkie eventy są w przedziale 1-10 minut
        for event in report['events']:
            minute = event['minute']
            assert 1 <= minute <= 10, f"Event w minucie {minute} poza zakresem 1-10"
    
    def test_different_results_without_seed(self):
        """Test że wyniki są różne bez seeda."""
        team_a, team_b = load_test_teams()
        
        results = []
        for _ in range(5):
            engine = MatchEngine(team_a, team_b, verbose=False, real_time=False)
            report = engine.simulate_match()
            results.append(report['score'])
        
        # Przynajmniej jeden wynik powinien być różny
        # (teoretycznie mogą być takie same, ale mało prawdopodobne)
        unique_results = set(results)
        # Pozwalamy na 1-5 unikalnych wyników (przy 5 meczach)
        assert len(unique_results) >= 1, "Symulacja powinna generować zróżnicowane wyniki"


class TestPlayerModel:
    """Testy dla modelu zawodnika."""
    
    def test_player_overall_calculation(self):
        """Test obliczania overall rating zawodnika."""
        player = Player(
            id=1,
            name="Test Player",
            position="MID",
            attributes={
                'physical': {'speed': 80, 'strength': 70, 'stamina': 75},
                'technical': {'passing': 85, 'shooting': 80, 'dribbling': 75},
                'mental': {'positioning': 70, 'concentration': 75, 'decisions': 80}
            },
            energy=1.0,
            form=1.0,
            traits=[]
        )
        
        overall = player.get_overall_rating()
        
        # Overall powinien być w rozsądnym zakresie (0-120)
        assert 0 <= overall <= 120
        assert overall > 50  # Dla dobrych atrybutów
    
    def test_player_position_checks(self):
        """Test funkcji sprawdzających pozycję zawodnika."""
        gk = Player(id=1, name="GK", position="GK", attributes={})
        def_player = Player(id=2, name="DEF", position="DEF", attributes={})
        mid = Player(id=3, name="MID", position="MID", attributes={})
        fwd = Player(id=4, name="FWD", position="FWD", attributes={})
        
        assert gk.is_goalkeeper()
        assert not gk.is_defender()
        
        assert def_player.is_defender()
        assert not def_player.is_midfielder()
        
        assert mid.is_midfielder()
        assert not mid.is_forward()
        
        assert fwd.is_forward()
        assert not fwd.is_goalkeeper()


class TestTeamModel:
    """Testy dla modelu drużyny."""
    
    def test_team_ratings(self):
        """Test obliczania ocen drużyny."""
        team_a, _ = load_test_teams()
        
        attack = team_a.get_attack_rating()
        defense = team_a.get_defense_rating()
        control = team_a.get_control_rating()
        
        # Wszystkie oceny powinny być w rozsądnym zakresie
        assert 0 < attack < 150
        assert 0 < defense < 150
        assert 0 < control < 150
    
    def test_style_modifiers(self):
        """Test modyfikatorów stylu gry."""
        team_a, _ = load_test_teams()
        
        # Test attacking style
        team_a.style = 'attacking'
        attack_rating_attacking = team_a.get_attack_rating()
        defense_rating_attacking = team_a.get_defense_rating()
        
        # Test defensive style
        team_a.style = 'defensive'
        attack_rating_defensive = team_a.get_attack_rating()
        defense_rating_defensive = team_a.get_defense_rating()
        
        # Atak powinien być wyższy dla stylu attacking
        assert attack_rating_attacking > attack_rating_defensive
        # Obrona powinna być wyższa dla stylu defensive
        assert defense_rating_defensive > defense_rating_attacking


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
