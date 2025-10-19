"""Uproszczony system pojedynków (Live Action Duels) dla silnika meczowego.

API:
  class DuelSystem:
      resolve_random_duel(att_player, def_player, att_team, def_team) -> dict

Zwracany słownik ma klucze:
  - outcome: 'win' | 'lose' | 'neutral'
  - type:    'dribble' | 'pass' | 'shot' | 'tackle'
  - detail:  opis tekstowy akcji
"""

from __future__ import annotations

import random
from typing import Dict, Optional

# Zakładamy, że Player posiada:
#   - name: str
#   - position: str
#   - attributes: {"physical": {...}, "technical": {...}, "mental": {...}}
# oraz że Team posiada:
#   - name: str
#   - style: 'attacking' | 'balanced' | 'defensive'
#   - attack_channel: 'wings' | 'center'


class DuelSystem:
    """Losowe pojedynki 1v1 z prostą logiką wyników i opisem narracyjnym."""

    ACTIONS = ("dribble", "pass", "shot", "tackle")

    def resolve_random_duel(self, att_player, def_player, att_team, def_team) -> Dict[str, str]:
        """Losuje rodzaj akcji i rozstrzyga pojedynek na bazie atrybutów + taktyki."""
        action = self._pick_action(att_team)
        outcome = "neutral"
        detail = ""

        # Wyznacz 'siłę' atakującego i broniącego pod tę akcję
        a_score = self._attacker_score(att_player, action, att_team)
        d_score = self._defender_score(def_player, action, def_team)

        # Szansa wygranej atakującego na bazie stosunku a/d (z RNG)
        p_win = self._sigmoid_ratio(a_score, d_score)

        roll = random.random()
        if roll < p_win * 0.92:  # lekkie "zaufanie" do przewagi
            outcome = "win"
        elif roll > max(0.05, 1.0 - (1.0 - p_win) * 0.92):
            outcome = "lose"
        else:
            outcome = "neutral"

        # Specjalne zachowanie dla "tackle": jeśli obrońca wygra, opisujemy odbiór/slajd
        if action == "tackle":
            if outcome == "win":
                # Wygrana atakującego przy wślizgu obrońcy = ominięcie wślizgu
                detail = f"{att_player.name} mija wślizg {def_player.name} i utrzymuje piłkę!"
            elif outcome == "lose":
                detail = f"{def_player.name} świetnym wślizgiem odbiera piłkę {att_player.name}!"
            else:
                detail = f"{att_player.name} próbuje minąć {def_player.name}, ale akcja wygasa."

        elif action == "dribble":
            if outcome == "win":
                detail = f"{att_player.name} mija {def_player.name} efektownym dryblingiem!"
            elif outcome == "lose":
                detail = f"{def_player.name} zatrzymuje drybling {att_player.name}."
            else:
                detail = f"{att_player.name} kiwa {def_player.name}, lecz tempo akcji spada."

        elif action == "pass":
            if outcome == "win":
                detail = f"{att_player.name} zagrywa precyzyjne podanie obok {def_player.name}!"
            elif outcome == "lose":
                detail = f"{def_player.name} przecina podanie {att_player.name}!"
            else:
                detail = f"{att_player.name} próbuje podać, ale {def_player.name} dobrze ustawia pressing."

        elif action == "shot":
            # Uwaga: sam strzał na bramkę i gol wylicza MatchEngine.
            if outcome == "win":
                detail = f"{att_player.name} znajduje pozycję do strzału mimo presji {def_player.name}!"
            elif outcome == "lose":
                detail = f"{def_player.name} nie pozwala {att_player.name} na oddanie strzału!"
            else:
                detail = f"{att_player.name} szykuje się do strzału, ale blok {def_player.name} w ostatniej chwili."

        return {
            "outcome": outcome,
            "type": action,
            "detail": detail,
        }

    # ────────────────────────────────────────────────────────────────────────
    # Heurystyki wyboru akcji i oceny atrybutów
    # ────────────────────────────────────────────────────────────────────────

    def _pick_action(self, att_team) -> str:
        """Dobór akcji zależny od stylu i kanału ataku."""
        base = {
            "dribble": 0.28,
            "pass":    0.32,
            "shot":    0.25,
            "tackle":  0.15,  # 'tackle' traktujemy jako starcie w obronie; tu pojawia się gdy pressing wysoki
        }
        style = (getattr(att_team, "style", "") or "").lower()
        channel = (getattr(att_team, "attack_channel", "") or "").lower()

        if style == "attacking":
            base["shot"] += 0.07
            base["dribble"] += 0.03
            base["pass"] -= 0.05
        elif style == "defensive":
            base["pass"] += 0.05
            base["shot"] -= 0.05

        if channel == "wings":
            base["dribble"] += 0.03
            base["pass"] += 0.02  # dośrodkowania/postraszenie wrzutką → liczymy jako pass

        # normalizacja
        total = sum(base.values())
        r = random.random() * total
        acc = 0.0
        for k, v in base.items():
            acc += v
            if r <= acc:
                return k
        return "pass"

    def _attacker_score(self, player, action: str, team) -> float:
        ph = self._avg(getattr(player, "attributes", {}).get("physical", {}))
        te = self._avg(getattr(player, "attributes", {}).get("technical", {}))
        me = self._avg(getattr(player, "attributes", {}).get("mental", {}))
        base = 0.5 * ph + 0.35 * te + 0.15 * me

        # waga pod akcję
        if action == "dribble":
            base *= 0.5 * self._safe(player, "attributes", "technical") + 0.5
        elif action == "pass":
            base *= 0.45 * self._safe(player, "attributes", "technical") + 0.55
        elif action == "shot":
            base *= 0.5 * self._safe(player, "attributes", "technical") + 0.5
        elif action == "tackle":
            # atakujący przy 'tackle' broni piłki, więc bardziej fizyka/mental
            base *= 0.5 * self._safe(player, "attributes", "physical") + 0.5

        style = (getattr(team, "style", "") or "").lower()
        if style == "attacking":
            base *= 1.06
        elif style == "defensive":
            base *= 0.96

        return max(1.0, base)

    def _defender_score(self, player, action: str, team) -> float:
        ph = self._avg(getattr(player, "attributes", {}).get("physical", {}))
        te = self._avg(getattr(player, "attributes", {}).get("technical", {}))
        me = self._avg(getattr(player, "attributes", {}).get("mental", {}))
        base = 0.45 * ph + 0.25 * te + 0.30 * me

        # w zależności od akcji atakującego inne wagi obrońcy
        if action in ("dribble", "tackle"):
            base *= 0.55 * self._safe(player, "attributes", "physical") + 0.45
        elif action == "pass":
            base *= 0.45 * self._safe(player, "attributes", "mental") + 0.55
        elif action == "shot":
            base *= 0.45 * self._safe(player, "attributes", "physical") + 0.55

        style = (getattr(team, "style", "") or "").lower()
        if style == "defensive":
            base *= 1.05
        elif style == "attacking":
            base *= 0.97

        return max(1.0, base)

    # ────────────────────────────────────────────────────────────────────────
    # Narzędzia
    # ────────────────────────────────────────────────────────────────────────

    def _avg(self, d: Dict[str, float]) -> float:
        if not d:
            return 60.0
        return sum(d.values()) / max(1, len(d))

    def _safe(self, player, root: str, sub: str) -> float:
        """Zwraca *znormalizowaną* średnią (0.6–1.4) dla danej grupy atrybutów."""
        try:
            group = getattr(player, root, {}).get(sub, {})
            avg = self._avg(group)
        except Exception:
            avg = 60.0
        # mapowanie 40–99 → 0.6–1.4 (z grubsza)
        norm = 0.6 + (max(40.0, min(99.0, avg)) - 40.0) * (0.8 / 59.0)
        return norm

    def _sigmoid_ratio(self, a: float, d: float) -> float:
        """Zwraca szansę wygranej atakującego na bazie stosunku a/d (miękka sigmoid)."""
        ratio = a / max(1.0, d)
        # zakres ratio 0.5–1.5 → ~0.27–0.73
        # łagodna krzywa; im większa przewaga, tym bliżej 0.8
        if ratio <= 0:
            return 0.25
        # prosta nieliniowa funkcja bez zależności od exp()
        base = 0.5 + (ratio - 1.0) * 0.35  # czułość
        return max(0.15, min(0.85, base))
