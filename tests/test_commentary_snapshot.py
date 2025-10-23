from __future__ import annotations
import pytest
from models.team import Team
from models.player import Player
from engine.match import MatchEngine
from engine.utils import set_random_seed


def _team(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [P(base+i, f"{name}{i}", pos) for i, pos in enumerate(["GK","DEF","DEF","MID","MID","MID","MID","DEF","FWD","FWD","FWD"])]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def test_commentary_variety_for_shots(monkeypatch: pytest.MonkeyPatch):
    A = _team('A', 3000)
    B = _team('B', 4000)

    def only_shots(self: MatchEngine, half: int, minute: int) -> None:
        # Pierwsze 5 minut: wymuszamy strzały A/B na zmianę
        if minute <= 5:
            attacker = self.team_a if minute % 2 == 1 else self.team_b
            shooter = attacker.players[8].name if len(attacker.players) > 8 else (attacker.players[0].name if attacker.players else 'Zawodnik')
            # naprzemiennie: celny/niecelny
            if minute % 2 == 1:
                self._emit_commentary(minute, 'shot_saved', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='shot_on_target')
            else:
                self._emit_commentary(minute, 'shot_off', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='shot_off_target')

    monkeypatch.setattr(MatchEngine, "_simulate_minute", only_shots, raising=True)
    set_random_seed(42)
    eng = MatchEngine(A, B, verbose=False, real_time=False)
    rep = eng.simulate_match()
    events = rep.get('events_full') or rep['events']
    # Zbierz linie komentarzy z pierwszych kilkunastu wpisów
    lines = [e['description'] for e in events[:20]]
    uniq = set(lines)
    assert len(uniq) >= 4

