"""Dodatkowe testy dla nowych funkcji silnika:
- precyzyjne liczenie strzałów po duelach
- logowanie czerwonej kartki w prawidłowej minucie
- podstawowy system zmian zawodników i obecność w raporcie
"""
from __future__ import annotations
import types
import pytest

from models.player import Player
from models.team import Team
from engine.match import MatchEngine


def _make_player(pid: int, name: str, pos: str, base: int = 70) -> Player:
    return Player(
        id=pid,
        name=name,
        position=pos,
        attributes={
            'physical': {'speed': base, 'strength': base, 'stamina': base},
            'technical': {'passing': base, 'shooting': base, 'dribbling': base, 'tackling': base, 'marking': base, 'reflexes': base, 'handling': base},
            'mental': {'positioning': base, 'concentration': base, 'decisions': base},
        },
        energy=1.0,
        form=1.0,
        traits=[]
    )


def _make_minimal_teams() -> tuple[Team, Team]:
    A = Team(
        name="A",
        players=[
            _make_player(1, "A GK", "GK"),
            _make_player(2, "A DEF", "DEF"),
            _make_player(3, "A MID", "MID"),
            _make_player(4, "A FWD", "FWD"),
            *_make_bodies(prefix="A", start_id=5)
        ],
        formation="4-4-2",
        style='balanced',
        attack_channel='center',
    )
    B = Team(
        name="B",
        players=[
            _make_player(101, "B GK", "GK"),
            _make_player(102, "B DEF", "DEF"),
            _make_player(103, "B MID", "MID"),
            _make_player(104, "B FWD", "FWD"),
            *_make_bodies(prefix="B", start_id=105)
        ],
        formation="4-4-2",
        style='balanced',
        attack_channel='center',
    )
    return A, B


def _make_bodies(prefix: str, start_id: int) -> list[Player]:
    # uzupełnij skład do min. 11 graczy
    out = []
    pid = start_id
    while len(out) < 7:  # już mamy 4, razem będzie 11
        pos = "MID" if len(out) % 2 == 0 else "DEF"
        out.append(_make_player(pid, f"{prefix} P{pid}", pos))
        pid += 1
    return out


def test_duel_shot_saved_counts_on_target(monkeypatch: pytest.MonkeyPatch):
    A, B = _make_minimal_teams()

    # Wymuś: w 1' tylko duel, brak fauli i brak zwykłych akcji
    def fake_minute(self: MatchEngine, half: int, minute: int) -> None:
        if minute == 1:
            self._simulate_duel(half, minute, self.team_a)
        # zero innych akcji

    monkeypatch.setattr(MatchEngine, "_simulate_minute", fake_minute, raising=True)

    # Zwróć strzał obroniony
    def fake_resolve(self, attacker, defender, *_):
        return {
            'type': 'shot',
            'outcome': 'shot',
            'shot_outcome': 'saved',
            'on_target': True,
            'detail': '',
            'scorer': getattr(attacker, 'name', 'A FWD'),
        }

    from engine.duel import DuelSystem
    monkeypatch.setattr(DuelSystem, "resolve_random_duel", fake_resolve, raising=True)

    eng = MatchEngine(A, B, verbose=False, real_time=False)
    rep = eng.simulate_match()

    assert rep['shots'][A.name] == 1
    assert rep['shots_on_target'][A.name] == 1
    assert rep['shots'][B.name] == 0
    assert rep['shots_on_target'][B.name] == 0


def test_duel_shot_wide_counts_off_target(monkeypatch: pytest.MonkeyPatch):
    A, B = _make_minimal_teams()

    def fake_minute(self: MatchEngine, half: int, minute: int) -> None:
        if minute == 1:
            self._simulate_duel(half, minute, self.team_a)

    monkeypatch.setattr(MatchEngine, "_simulate_minute", fake_minute, raising=True)

    def fake_resolve(self, attacker, defender, *_):
        return {
            'type': 'shot',
            'outcome': 'shot',
            'shot_outcome': 'wide',
            'on_target': False,
            'detail': '',
            'scorer': getattr(attacker, 'name', 'A FWD'),
        }

    from engine.duel import DuelSystem
    monkeypatch.setattr(DuelSystem, "resolve_random_duel", fake_resolve, raising=True)

    eng = MatchEngine(A, B, verbose=False, real_time=False)
    rep = eng.simulate_match()

    assert rep['shots'][A.name] == 1
    assert rep['shots_on_target'][A.name] == 0


def test_red_card_minute_is_not_zero(monkeypatch: pytest.MonkeyPatch):
    A, B = _make_minimal_teams()

    # Wymuś faul w 1' i bez innych zdarzeń
    def fake_minute(self: MatchEngine, half: int, minute: int) -> None:
        if minute == 1:
            self._simulate_foul(half, minute, self.team_a)

    monkeypatch.setattr(MatchEngine, "_simulate_minute", fake_minute, raising=True)

    # Ustaw zawsze czerwoną bez żółtej
    import engine.match as em
    monkeypatch.setattr(em, "DIRECT_RED_PROB", 1.0, raising=False)
    monkeypatch.setattr(em, "YELLOW_PROB", 0.0, raising=False)

    eng = MatchEngine(A, B, verbose=False, real_time=False)
    rep = eng.simulate_match()
    reds = [e for e in rep['events_full'] if e['event_type'] == 'red_card']
    assert reds, "Powinna pojawić się czerwona kartka"
    assert all(e['minute'] >= 1 for e in reds), "Minuta czerwonej kartki nie może być 0"


def test_substitutions_present_with_bench():
    # Dajemy ławkę – 14 graczy na zespół
    def make_team_with_bench(name: str, base_id: int) -> Team:
        players = [
            _make_player(base_id + 0, f"{name} GK", "GK"),
            _make_player(base_id + 1, f"{name} DEF1", "DEF"),
            _make_player(base_id + 2, f"{name} DEF2", "DEF"),
            _make_player(base_id + 3, f"{name} DEF3", "DEF"),
            _make_player(base_id + 4, f"{name} MID1", "MID"),
            _make_player(base_id + 5, f"{name} MID2", "MID"),
            _make_player(base_id + 6, f"{name} MID3", "MID"),
            _make_player(base_id + 7, f"{name} MID4", "MID"),
            _make_player(base_id + 8, f"{name} FWD1", "FWD"),
            _make_player(base_id + 9, f"{name} FWD2", "FWD"),
            _make_player(base_id +10, f"{name} FWD3", "FWD"),
            # ławka
            _make_player(base_id +11, f"{name} BENCH1", "DEF"),
            _make_player(base_id +12, f"{name} BENCH2", "MID"),
            _make_player(base_id +13, f"{name} BENCH3", "FWD"),
        ]
        return Team(name=name, players=players, formation="4-4-2", style='balanced', attack_channel='center')

    A = make_team_with_bench("A", 1000)
    B = make_team_with_bench("B", 2000)

    eng = MatchEngine(A, B, verbose=False, real_time=False)
    rep = eng.simulate_match()
    subs = rep.get('substitutions') or []
    assert len(subs) >= 2, "Powinny wystąpić zmiany przy ławce – 60' i 75'"
    minutes = {s['minute'] for s in subs}
    assert minutes & {60, 75}, "Zmiany powinny pojawić się około 60' lub 75'"

