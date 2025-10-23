"""Model zawodnika piłkarskiego."""
from dataclasses import dataclass, field
from typing import List, Dict, Literal


@dataclass
class Player:
    """
    Reprezentuje zawodnika piłkarskiego.
    
    Attributes:
        id: Unikalny identyfikator zawodnika
        name: Imię i nazwisko zawodnika
        position: Pozycja (GK/DEF/MID/FWD)
        attributes: Słownik atrybutów podzielonych na kategorie
        energy: Energia zawodnika (0.7-1.0), wpływa na performance
        form: Forma zawodnika (0.0-1.0), wpływa na skuteczność
        traits: Lista cech charakteru (np. 'Ambitious', 'Loyal')
    """
    id: int
    name: str
    position: str  # GK, DEF, MID, FWD
    attributes: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # attributes struktura: {'physical': {}, 'technical': {}, 'mental': {}}
    energy: float = 1.0  # normalized 0.0-1.0 (back-compat)
    stamina_base: int = 75  # 1-100 baseline stamina for fatigue model
    work_rate: Literal["low","med","high"] = "med"
    distance_km: float = 0.0
    form: float = 1.0    # 0.0-1.0
    traits: List[str] = field(default_factory=list)
    
    def get_overall_rating(self) -> float:
        """
        Oblicza ogólną ocenę zawodnika.
        
        Wzór: 0.5*mean(physical) + 0.35*mean(technical) + 0.15*mean(mental)
        Pomnożone przez współczynniki form i energy.
        
        Returns:
            Ogólna ocena zawodnika (0-100)
        """
        physical_avg = self._calculate_category_average('physical')
        technical_avg = self._calculate_category_average('technical')
        mental_avg = self._calculate_category_average('mental')
        
        # Wagi: 50% physical, 35% technical, 15% mental
        base_overall = (
            0.5 * physical_avg +
            0.35 * technical_avg +
            0.15 * mental_avg
        )
        
        # Modyfikatory: forma (0.8-1.2 range) i energia (0.7-1.0)
        form_modifier = 0.8 + (self.form * 0.4)  # form 0.0->0.8, form 1.0->1.2
        energy_modifier = self.energy
        
        return base_overall * form_modifier * energy_modifier

    @property
    def overall(self) -> float:
        """Źródło prawdy dla Overall w całym projekcie.

        Zwraca wynik metody obliczeniowej `get_overall_rating()`.
        Wszędzie poza modelami/algorytmami należy odwoływać się do
        `player.overall`, a nie lokalnie liczyć średnie.
        """
        return self.get_overall_rating()

    # Alias pomocniczy zgodny z kanonem nazw w projekcie
    def get_overall(self) -> float:
        """Alias do `get_overall_rating()` dla wygody/zgodności."""
        return self.get_overall_rating()
    
    def _calculate_category_average(self, category: str) -> float:
        """Oblicza średnią z danej kategorii atrybutów."""
        if category not in self.attributes or not self.attributes[category]:
            return 50.0  # Wartość domyślna
        
        values = list(self.attributes[category].values())
        return sum(values) / len(values) if values else 50.0
    
    def get_attribute(self, category: str, attribute_name: str) -> int:
        """Pobiera konkretny atrybut zawodnika."""
        if category in self.attributes and attribute_name in self.attributes[category]:
            return self.attributes[category][attribute_name]
        return 50  # Wartość domyślna
    
    def is_goalkeeper(self) -> bool:
        """Sprawdza czy zawodnik jest bramkarzem."""
        return self.position == 'GK'
    
    def is_defender(self) -> bool:
        """Sprawdza czy zawodnik jest obrońcą."""
        return self.position == 'DEF'
    
    def is_midfielder(self) -> bool:
        """Sprawdza czy zawodnik jest pomocnikiem."""
        return self.position == 'MID'
    
    def is_forward(self) -> bool:
        """Sprawdza czy zawodnik jest napastnikiem."""
        return self.position == 'FWD'
