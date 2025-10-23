from __future__ import annotations
import pytest

from engine.match import MatchEngine
from engine.utils import set_random_seed
from models.team import Team
from models.player import Player


def _team(name: str, base: int) -> Team:
    def P(i, nm, pos):
        return Player(id=i, name=nm, position=pos,
                      attributes={'physical':{'speed':70,'strength':70,'stamina':80},
                                  'technical':{'passing':70,'shooting':65,'dribbling':65,'tackling':70,'marking':70,'reflexes':60,'handling':60},
                                  'mental':{'positioning':65,'concentration':65,'decisions':60,'aggression':50}},
                      energy=1.0, form=1.0, traits=[])
    players = [P(base+i, f"{name}{i}", pos) for i, pos in enumerate(["GK","DEF","DEF","MID","MID","MID","MID","DEF","FWD","FWD","FWD"])]
    return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')


def test_global_cooldown_commentary(monkeypatch: pytest.MonkeyPatch):
    A = _team('A', 6000)
    B = _team('B', 7000)

    def only_shots(self: MatchEngine, half: int, minute: int) -> None:
        attacker = self.team_a if (minute % 2 == 1) else self.team_b
        shooter = attacker.players[8].name if len(attacker.players) > 8 else (attacker.players[0].name if attacker.players else 'Zawodnik')
        # Naprzemiennie celny/niecelny
        if minute % 2 == 1:
            self._emit_commentary(minute, 'shot_saved', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='shot_on_target')
        else:
            self._emit_commentary(minute, 'shot_off', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='shot_off_target')

    monkeypatch.setattr(MatchEngine, "_simulate_minute", only_shots, raising=True)
    set_random_seed(42)
    eng = MatchEngine(A, B, verbose=False, real_time=False)
    # Symuluj dokładnie 30 zdarzeń (minut)
    for m in range(1, 31):
        eng._simulate_minute(1 if m <= 15 else 2, m)
    # zbuduj raport i pobierz wszystkie linie (bez mikro)
    rep = eng._build_report()
    events = [e for e in rep.get('events_full') or rep['events'] if e['event_type'] != 'micro']
    lines = [e['description'] for e in events]
    # min. 80% unikalnych linii
    uniq_ratio = len(set(lines)) / max(1, len(lines))
    assert uniq_ratio >= 0.8
    # brak dwóch identycznych linii w odległości < 4
    for i in range(len(lines)):
        for j in range(i+1, min(len(lines), i+4)):
            assert lines[i] != lines[j]

