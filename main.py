"""
Główny punkt wejścia dla symulatora meczu piłkarskiego.

Uruchomienie: python main.py --teamA "Red Lions" --teamB "Blue Hawks" --seed 42 --verbose
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from models.player import Player
from models.team import Team
from engine.match import MatchEngine
from engine.utils import set_random_seed


def load_teams_from_json(filepath: str = 'data/teams.json') -> Dict[str, Team]:
    """
    Ładuje dane drużyn z pliku JSON.
    
    Args:
        filepath: Ścieżka do pliku JSON
        
    Returns:
        Słownik z nazwą drużyny jako kluczem i obiektem Team jako wartością
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    teams = {}
    for team_data in data['teams']:
        # Konwertuj dane zawodników na obiekty Player
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
        
        # Utwórz obiekt Team
        team = Team(
            name=team_data['name'],
            players=players,
            formation=team_data.get('formation', '4-4-2'),
            style=team_data.get('style', 'balanced'),
            attack_channel=team_data.get('attack_channel', 'center')
        )
        teams[team.name] = team
    
    return teams


def print_match_report(report: Dict) -> None:
    """
    Wypisuje szczegółowy raport z meczu w czytelnym formacie.
    
    Args:
        report: Słownik z raportem z meczu
    """
    print("\n" + "="*70)
    print(f"RAPORT Z MECZU: {report['team_a']} vs {report['team_b']}")
    print("="*70)
    
    # Wynik końcowy
    print(f"\n📊 WYNIK KOŃCOWY: {report['team_a']} {report['score'][0]} - {report['score'][1]} {report['team_b']}")
    
    # Bramki
    if report['goals']:
        print(f"\n⚽ BRAMKI ({len(report['goals'])}):")
        for goal in report['goals']:
            print(f"   {goal['minute']}' - {goal['scorer']} ({goal['team']})")
    else:
        print("\n⚽ BRAMKI: Brak bramek w tym meczu")
    
    # Statystyki
    print(f"\n📈 STATYSTYKI:")
    print(f"   Posiadanie piłki:")
    print(f"      {report['team_a']}: {report['possession'][report['team_a']]}%")
    print(f"      {report['team_b']}: {report['possession'][report['team_b']]}%")
    
    print(f"\n   Strzały:")
    print(f"      {report['team_a']}: {report['shots'][report['team_a']]} ({report['shots_on_target'][report['team_a']]} celnych)")
    print(f"      {report['team_b']}: {report['shots'][report['team_b']]} ({report['shots_on_target'][report['team_b']]} celnych)")
    
    # Wpływ taktyki
    if 'tactical_impact' in report:
        tactical = report['tactical_impact']
        print(f"\n⚙️  ANALIZA TAKTYCZNA:")
        print(f"   {report['team_a']} (styl: {tactical['team_a_style']}) - Skuteczność strzałów: {tactical['shots_efficiency_a']}%")
        print(f"   {report['team_b']} (styl: {tactical['team_b_style']}) - Skuteczność strzałów: {tactical['shots_efficiency_b']}%")
    
    # Zmiany
    if 'substitutions' in report and report['substitutions']:
        print(f"\n🔄 ZMIANY ({len(report['substitutions'])}):")
        for sub in report['substitutions']:
            print(f"   {sub['minute']}' - {sub['team']}: {sub['player_out']} (powód: {sub['reason']})")
    
    # Kluczowe zdarzenia
    important_events = [e for e in report['events'] if e['event_type'] in ['goal', 'shot_saved', 'successful_dribble']]
    if important_events:
        print(f"\n🔥 KLUCZOWE ZDARZENIA ({len(important_events)}):")
        for event in important_events[:15]:  # Pokaż max 15 najważniejszych
            print(f"   {event['minute']}' - {event['description']} ({event['team']})")
    
    print("\n" + "="*80)


def main():
    """Główna funkcja programu."""
    parser = argparse.ArgumentParser(
        description='Symulator meczu piłkarskiego - Football Manager Match Engine'
    )
    parser.add_argument(
        '--teamA',
        type=str,
        default='Red Lions',
        help='Nazwa pierwszej drużyny (domyślnie: Red Lions)'
    )
    parser.add_argument(
        '--teamB',
        type=str,
        default='Blue Hawks',
        help='Nazwa drugiej drużyny (domyślnie: Blue Hawks)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Seed dla generatora losowego (dla powtarzalności wyników)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Wyświetl szczegółowe informacje podczas symulacji'
    )
    
    args = parser.parse_args()
    
    # Ustaw seed jeśli podano
    if args.seed is not None:
        set_random_seed(args.seed)
        print(f"🎲 Ustawiono seed: {args.seed} (wynik będzie powtarzalny)")
    
    # Załaduj drużyny
    try:
        teams = load_teams_from_json('data/teams.json')
    except FileNotFoundError:
        print("❌ Błąd: Nie znaleziono pliku data/teams.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Błąd parsowania JSON: {e}")
        sys.exit(1)
    
    # Sprawdź czy drużyny istnieją
    if args.teamA not in teams:
        print(f"❌ Błąd: Drużyna '{args.teamA}' nie istnieje w pliku teams.json")
        print(f"   Dostępne drużyny: {', '.join(teams.keys())}")
        sys.exit(1)
    
    if args.teamB not in teams:
        print(f"❌ Błąd: Drużyna '{args.teamB}' nie istnieje w pliku teams.json")
        print(f"   Dostępne drużyny: {', '.join(teams.keys())}")
        sys.exit(1)
    
    team_a = teams[args.teamA]
    team_b = teams[args.teamB]
    
    # Utwórz silnik meczowy i symuluj
    print(f"\n⚽ FOOTBALL MANAGER - MATCH ENGINE")
    print(f"   Mecz: {team_a.name} vs {team_b.name}")
    print(f"   Czas trwania: 10 minut (5 min każda połowa)\n")
    
    engine = MatchEngine(team_a, team_b, verbose=True, real_time=False)
    report = engine.simulate_match()
    
    # Wyświetl raport
    print_match_report(report)


if __name__ == "__main__":
    main()
