"""Model drużyny piłkarskiej."""
from dataclasses import dataclass, field
from typing import List, Optional
from models.player import Player


@dataclass
class Team:
    """
    Reprezentuje drużynę piłkarską.
    
    Attributes:
        name: Nazwa drużyny
        players: Lista zawodników (11 w podstawowym składzie)
        formation: Ustawienie taktyczne (np. '4-4-2', '4-3-3')
        style: Styl gry ('defensive', 'balanced', 'attacking')
        attack_channel: Kanał ataku ('wings', 'center')
    """
    name: str
    players: List[Player] = field(default_factory=list)
    formation: str = '4-4-2'
    style: str = 'balanced'  # defensive, balanced, attacking
    attack_channel: str = 'center'  # wings, center
    pressing: str = 'normal'        # low, normal, high
    width: str = 'normal'           # narrow, normal, wide

    def pressing_level(self) -> int:
        p = (self.pressing or 'normal').lower()
        if p == 'high':
            return 1
        if p == 'low':
            return -1
        return 0

    def width_level(self) -> int:
        w = (self.width or 'normal').lower()
        if w in ('wide', 'wings'):
            return 1
        if w in ('narrow', 'narrower'):
            return -1
        return 0
    
    def get_attack_rating(self) -> float:
        """
        Oblicza siłę ataku drużyny.
        
        Bierze pod uwagę najlepszych 5 napastników/pomocników ważonych.
        
        Returns:
            Ocena ataku drużyny
        """
        attackers = [p for p in self.players if p.is_forward() or p.is_midfielder()]
        if not attackers:
            return 50.0
        
        # Sortuj po overall i weź top 5
        attackers.sort(key=lambda p: p.get_overall_rating(), reverse=True)
        top_attackers = attackers[:5]
        
        base_attack = sum(p.get_overall_rating() for p in top_attackers) / len(top_attackers)
        
        # Modyfikator stylu
        attack_modifier = self._get_style_modifier()['attack']
        
        return base_attack * attack_modifier
    
    def get_defense_rating(self) -> float:
        """
        Oblicza siłę obrony drużyny.
        
        Bierze pod uwagę najlepszych 5 obrońców/bramkarzy.
        
        Returns:
            Ocena obrony drużyny
        """
        defenders = [p for p in self.players if p.is_defender() or p.is_goalkeeper()]
        if not defenders:
            return 50.0
        
        # Sortuj po overall i weź top 5
        defenders.sort(key=lambda p: p.get_overall_rating(), reverse=True)
        top_defenders = defenders[:5]
        
        base_defense = sum(p.get_overall_rating() for p in top_defenders) / len(top_defenders)
        
        # Modyfikator stylu
        defense_modifier = self._get_style_modifier()['defense']
        
        return base_defense * defense_modifier
    
    def get_control_rating(self) -> float:
        """
        Oblicza kontrolę drużyny (średnia całego składu).
        
        Returns:
            Ocena kontroli drużyny
        """
        if not self.players:
            return 50.0
        
        return sum(p.get_overall_rating() for p in self.players) / len(self.players)
    
    def _get_style_modifier(self) -> dict:
        """
        Zwraca modyfikatory na podstawie stylu gry.
        
        Returns:
            Dict z modyfikatorami dla ataku i obrony
        """
        if self.style == 'attacking':
            return {'attack': 1.10, 'defense': 0.95}
        elif self.style == 'defensive':
            return {'attack': 0.95, 'defense': 1.10}
        else:  # balanced
            return {'attack': 1.0, 'defense': 1.0}
    
    def get_goalkeeper(self) -> Optional[Player]:
        """Zwraca bramkarza drużyny."""
        goalkeepers = [p for p in self.players if p.is_goalkeeper()]
        if goalkeepers:
            return goalkeepers[0]
        # Fallback: pierwszy zawodnik
        return self.players[0] if self.players else None
    
    def get_attackers(self) -> List[Player]:
        """Zwraca listę napastników."""
        return [p for p in self.players if p.is_forward()]
    
    def get_midfielders(self) -> List[Player]:
        """Zwraca listę pomocników."""
        return [p for p in self.players if p.is_midfielder()]
    
    def get_defenders(self) -> List[Player]:
        """Zwraca listę obrońców."""
        return [p for p in self.players if p.is_defender()]
    
    def get_random_outfield_player(self, position_preference: Optional[str] = None) -> Player:
        """
        Zwraca losowego zawodnika z pola (nie bramkarza).
        
        Args:
            position_preference: Preferowana pozycja ('wings' lub 'center')
            
        Returns:
            Losowy zawodnik
        """
        import random
        
        outfield = [p for p in self.players if not p.is_goalkeeper()]
        
        if position_preference == 'wings' and self.attack_channel == 'wings':
            # Preferuj skrzydłowych (pomocnicy i napastnicy)
            wings_players = [p for p in outfield if p.is_midfielder() or p.is_forward()]
            if wings_players:
                return random.choice(wings_players)
        elif position_preference == 'center':
            # Preferuj środkowych (pomocnicy)
            center_players = [p for p in outfield if p.is_midfielder()]
            if center_players:
                return random.choice(center_players)
        
        return random.choice(outfield) if outfield else self.players[0]
