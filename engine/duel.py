"""System Live Action Duel - pojedynki zawodników podczas meczu."""
import random
from typing import Dict, Tuple, Optional
from models.player import Player
from models.team import Team


class DuelSystem:
    """
    System pojedynków zawodników (Live Action Duels).
    
    Wybiera zawodników, akcje i rozstrzyga na podstawie atrybutów i RNG.
    """
    
    ACTIONS = ['dribble', 'pass', 'shot', 'tackle']
    
    def __init__(self, verbose: bool = False):
        """
        Inicjalizuje system pojedynków.
        
        Args:
            verbose: Czy wypisywać dodatkowe informacje
        """
        self.verbose = verbose
    
    def execute_duel(
        self,
        attacking_team: Team,
        defending_team: Team,
        minute: int
    ) -> Dict:
        """
        Wykonuje pojedynek między zawodnikami.
        
        Args:
            attacking_team: Drużyna atakująca
            defending_team: Drużyna broniąca
            minute: Minuta meczu
            
        Returns:
            Słownik z wynikiem pojedynku
        """
        # Wybierz zawodników
        attacker = self._select_attacker(attacking_team)
        defender = self._select_defender(defending_team)
        goalkeeper = defending_team.get_goalkeeper()
        
        # Losuj akcję dla atakującego
        attacker_action = random.choice(['dribble', 'pass', 'shot'])
        defender_action = random.choice(['tackle', 'intercept'])
        
        # Rozstrzygnij pojedynek
        result = self._resolve_duel(
            attacker, attacker_action,
            defender, defender_action,
            goalkeeper, attacking_team
        )
        
        # Dodaj kontekst
        result['minute'] = minute
        result['team'] = attacking_team.name
        result['players'] = [attacker.name, defender.name]
        
        if self.verbose:
            print(f"  [DUEL] {minute}' - {attacker.name} ({attacker_action}) vs {defender.name} ({defender_action})")
            print(f"         Result: {result['event_type']}")
        
        return result
    
    def _select_attacker(self, team: Team) -> Player:
        """Wybiera zawodnika atakującego z preferowanego kanału."""
        if team.attack_channel == 'wings':
            # Preferuj skrzydłowych i napastników
            candidates = [p for p in team.players if p.is_forward() or p.is_midfielder()]
        else:
            # Preferuj środkowych pomocników i napastników
            candidates = [p for p in team.players if p.is_midfielder() or p.is_forward()]
        
        if not candidates:
            candidates = [p for p in team.players if not p.is_goalkeeper()]
        
        # Wybierz z wagami według overall rating
        weights = [p.get_overall_rating() for p in candidates]
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(candidates)
        
        normalized_weights = [w / total_weight for w in weights]
        return random.choices(candidates, weights=normalized_weights)[0]
    
    def _select_defender(self, team: Team) -> Player:
        """Wybiera zawodnika broniącego."""
        defenders = [p for p in team.players if p.is_defender()]
        
        if not defenders:
            defenders = [p for p in team.players if not p.is_goalkeeper()]
        
        # Wybierz z wagami według overall rating
        weights = [p.get_overall_rating() for p in defenders]
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(defenders)
        
        normalized_weights = [w / total_weight for w in weights]
        return random.choices(defenders, weights=normalized_weights)[0]
    
    def _resolve_duel(
        self,
        attacker: Player,
        attacker_action: str,
        defender: Player,
        defender_action: str,
        goalkeeper: Optional[Player],
        attacking_team: Team
    ) -> Dict:
        """
        Rozstrzyga pojedynek na podstawie atrybutów i akcji.
        
        Returns:
            Dict z event_type i description
        """
        # Pobierz kluczowe atrybuty
        attacker_skill = attacker.get_overall_rating()
        defender_skill = defender.get_overall_rating()
        
        # Bazowa szansa sukcesu atakującego
        success_chance = 0.5 + (attacker_skill - defender_skill) / 200.0
        success_chance = max(0.2, min(0.8, success_chance))  # Ograniczenie 20-80%
        
        # Losowanie
        roll = random.random()
        
        if attacker_action == 'shot':
            return self._resolve_shot(attacker, goalkeeper, success_chance > roll)
        elif attacker_action == 'dribble':
            if success_chance > roll:
                return {
                    'event_type': 'successful_dribble',
                    'description': f'{attacker.name} znakomicie drybluje {defender.name}!',
                    'possession_retained': True
                }
            else:
                return {
                    'event_type': 'lost_possession',
                    'description': f'{defender.name} odbiera piłkę {attacker.name}',
                    'possession_retained': False
                }
        elif attacker_action == 'pass':
            if success_chance > roll:
                return {
                    'event_type': 'successful_pass',
                    'description': f'{attacker.name} dokładne podanie',
                    'possession_retained': True
                }
            else:
                return {
                    'event_type': 'intercepted_pass',
                    'description': f'{defender.name} przechwyca podanie',
                    'possession_retained': False
                }
        
        # Domyślnie
        return {
            'event_type': 'lost_possession',
            'description': f'Piłka przechodzi do {defender.name}',
            'possession_retained': False
        }
    
    def _resolve_shot(
        self,
        shooter: Player,
        goalkeeper: Optional[Player],
        attack_successful: bool
    ) -> Dict:
        """
        Rozstrzyga strzał na bramkę.
        
        Args:
            shooter: Zawodnik strzelający
            goalkeeper: Bramkarz
            attack_successful: Czy atak był udany (przeszedł obronę)
            
        Returns:
            Dict z wynikiem strzału
        """
        if not attack_successful:
            return {
                'event_type': 'shot_blocked',
                'description': f'Strzał {shooter.name} zablokowany przez obronę',
                'possession_retained': False
            }
        
        # Oblicz szansę na gola
        shooting_skill = shooter.get_attribute('technical', 'shooting')
        positioning = shooter.get_attribute('technical', 'positioning')
        gk_reflexes = goalkeeper.get_attribute('technical', 'reflexes') if goalkeeper else 50
        gk_positioning = goalkeeper.get_attribute('mental', 'positioning') if goalkeeper else 50
        
        shooter_rating = (shooting_skill + positioning) / 2
        gk_rating = (gk_reflexes + gk_positioning) / 2
        
        # Szansa na celny strzał
        on_target_chance = shooter_rating / 100.0
        on_target_chance = max(0.3, min(0.9, on_target_chance))
        
        if random.random() > on_target_chance:
            return {
                'event_type': 'shot_off_target',
                'description': f'{shooter.name} strzela niecelnie!',
                'possession_retained': False
            }
        
        # Strzał celny - czy będzie gol?
        goal_chance = 0.4 + (shooter_rating - gk_rating) / 200.0
        goal_chance = max(0.15, min(0.7, goal_chance))
        
        if random.random() < goal_chance:
            return {
                'event_type': 'goal',
                'description': f'GOOOOL! {shooter.name} strzela bramkę!',
                'scorer': shooter.name,
                'possession_retained': False
            }
        else:
            return {
                'event_type': 'shot_saved',
                'description': f'{shooter.name} strzela, ale {goalkeeper.name if goalkeeper else "bramkarz"} broni!',
                'possession_retained': False
            }
