"""Funkcje pomocnicze dla silnika meczowego."""
import random
from typing import Dict, Optional
from models.team import Team


def set_random_seed(seed: Optional[int] = None) -> None:
    """
    Ustawia seed dla generatora liczb losowych.
    
    Args:
        seed: Seed dla reproducibility (None = losowy)
    """
    if seed is not None:
        random.seed(seed)


def calculate_team_strength(team: Team) -> Dict[str, float]:
    """
    Oblicza kompleksową siłę drużyny.
    
    Args:
        team: Drużyna do oceny
        
    Returns:
        Słownik z oceną ataku, obrony i kontroli
    """
    return {
        'attack': team.get_attack_rating(),
        'defense': team.get_defense_rating(),
        'control': team.get_control_rating(),
        'overall': (team.get_attack_rating() + team.get_defense_rating() + team.get_control_rating()) / 3
    }


def calculate_probability(base_value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Normalizuje wartość do zakresu prawdopodobieństwa.
    
    Args:
        base_value: Wartość bazowa
        min_val: Minimalna wartość
        max_val: Maksymalna wartość
        
    Returns:
        Wartość znormalizowana
    """
    return max(min_val, min(max_val, base_value))


def weighted_random_choice(options: list, weights: list):
    """
    Wybiera losowy element z listy z wagami.
    
    Args:
        options: Lista opcji
        weights: Lista wag (nie muszą sumować się do 1)
        
    Returns:
        Wybrany element
    """
    if not options or not weights:
        return None
    
    total = sum(weights)
    if total == 0:
        return random.choice(options)
    
    normalized_weights = [w / total for w in weights]
    return random.choices(options, weights=normalized_weights)[0]
