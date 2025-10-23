from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from models.team import Team
from models.player import Player
from engine.fatigue import apply_fatigue_tick, FatigueContext, halftime_regen
from engine.injury import maybe_injury
from engine.duel import DuelSystem

# Eksportowane stałe (używane w main.py)
TOTAL_SIM_MINUTES = 90
DEFAULT_REAL_MINUTES = 8

@dataclass
class MatchStats:
    shots_a: int = 0
    shots_on_a: int = 0
    shots_b: int = 0
    shots_on_b: int = 0
    corners_a: int = 0
    corners_b: int = 0
    freekicks_a: int = 0
    freekicks_b: int = 0
    penalties_a: int = 0
    penalties_b: int = 0
    fouls_a: int = 0
    fouls_b: int = 0
    yellows_a: int = 0
    yellows_b: int = 0
    reds_a: int = 0
    reds_b: int = 0
    duels_won_a: int = 0
    duels_won_b: int = 0
    duels_total_a: int = 0
    duels_total_b: int = 0
    goals_a: List[Tuple[int, str, Optional[str]]] = field(default_factory=list)
    goals_b: List[Tuple[int, str, Optional[str]]] = field(default_factory=list)

class MatchEngine:
    def __init__(self, team_a: Team, team_b: Team, *, verbose: bool = False, real_time: bool = False,
                 real_minutes_target: int = DEFAULT_REAL_MINUTES, density: str = "high", referee_profile: str = "random") -> None:
        self.team_a = team_a
        self.team_b = team_b
        self.verbose = verbose
        self.real_time = real_time
        self.real_minutes_target = max(2, min(30, int(real_minutes_target)))
        self.density = density
        self.stats = MatchStats()
        self.possession_a_ticks = 0
        self.possession_b_ticks = 0
        self._rng = random.Random()
        self._events: List[Dict] = []
        # uproszczony sędzia (zgodne z main.py)
        self.referee = {"key": "neutral", "label": "Neutralny", "foul_mult": 1.0, "yellow_mult": 1.0, "red_mult": 1.0}
        self.duels = DuelSystem()
        self.substitutions: List[Dict] = []

    def _add_event(self, minute: int, kind: str, text: str) -> None:
        self._events.append({"kind": kind, "text": text, "minute": minute})
        if self.verbose:
            print(text)

    def simulate_match(self) -> Dict:
        total_minutes = TOTAL_SIM_MINUTES
        # start
        self._add_event(0, "banner", f"Mecz: {self.team_a.name} vs {self.team_b.name}")
        # pętla minutowa (prosty model)
        for minute in range(1, total_minutes + 1):
            # proste okienka zmian (jeśli skład > 11)
            if minute in (60, 75):
                self._maybe_substitution(minute, self.team_a)
                self._maybe_substitution(minute, self.team_b)
            # posiadanie (prosty dryf)
            if self._rng.random() < 0.5:
                self.possession_a_ticks += 1
                attacker = self.team_a
                defender = self.team_b
            else:
                self.possession_b_ticks += 1
                attacker = self.team_b
                defender = self.team_a
            roll = self._rng.random()
            # faul (rzadko)
            if roll < 0.06:
                self._simulate_foul(minute, attacker, defender)
            # pojedynek (średnio)
            elif roll < 0.18:
                self._simulate_duel(minute, attacker, defender)
            # SFG (rzut rożny / wolny / karny)
            elif roll < 0.26:
                self._simulate_set_piece(minute, attacker, defender)
            # akcja/strzał
            elif roll < 0.52:
                shooter = self._rng.choice(attacker.players).name if attacker.players else "Zawodnik"
                on_target = self._rng.random() < 0.60
                if attacker is self.team_a:
                    self.stats.shots_a += 1
                    if on_target: self.stats.shots_on_a += 1
                else:
                    self.stats.shots_b += 1
                    if on_target: self.stats.shots_on_b += 1
                goal = on_target and (self._rng.random() < 0.18)
                if goal:
                    if attacker is self.team_a:
                        self.stats.goals_a.append((minute, shooter, None))
                    else:
                        self.stats.goals_b.append((minute, shooter, None))
                    self._add_event(minute, "goal", f"{minute}' - GOL! {attacker.name}! Strzelec: {shooter}")
                else:
                    if on_target:
                        self._add_event(minute, "shot_on_target", f"{minute}' - {shooter} celnie — dobra interwencja bramkarza!")
                    else:
                        self._add_event(minute, "shot_off_target", f"{minute}' - {shooter} niecelnie!")
            # Fatigue tick + injuries
            try:
                ctx = FatigueContext(minute=minute, team_in_possession=attacker, defending_team=defender)
                active_a = attacker.players[:min(11, len(attacker.players))]
                active_b = defender.players[:min(11, len(defender.players))]
                apply_fatigue_tick(active_a, active_b, ctx)
                # injuries (bardzo rzadko): po 1 kandydacie na zespół
                if active_a and self._rng.random() < 0.01:
                    vic = self._rng.choice(active_a)
                    evt = maybe_injury(vic, minute, attacker, strict_ref=False, opponent_high_press=False)
                    if evt and evt.requires_sub:
                        self._add_event(minute, "injury", f"{minute}' - Kontuzja! {vic.name} schodzi z urazem ({evt.type})")
                if active_b and self._rng.random() < 0.01:
                    vic2 = self._rng.choice(active_b)
                    evt2 = maybe_injury(vic2, minute, defender, strict_ref=False, opponent_high_press=False)
                    if evt2 and evt2.requires_sub:
                        self._add_event(minute, "injury", f"{minute}' - Kontuzja! {vic2.name} schodzi z urazem ({evt2.type})")
            except Exception:
                pass

            # RT
            if self.real_time:
                time.sleep((self.real_minutes_target * 60.0) / TOTAL_SIM_MINUTES)
        # koniec
        self._add_event(90, "final_whistle", "Koniec meczu!")
        return self._build_report()

    def _maybe_substitution(self, minute: int, team: Team) -> None:
        # jeśli nie ma ławki – pomiń
        if len(team.players) <= 11:
            return
        # wybierz „zmęczonego” (na razie losowo) i rezerwowego z ławki
        out_idx = self._rng.randint(0, 10)
        bench_idx = self._rng.randint(11, len(team.players) - 1)
        out_p = team.players[out_idx]
        in_p = team.players[bench_idx]
        team.players[out_idx], team.players[bench_idx] = in_p, out_p
        self._add_event(minute, "substitution", f"{minute}' - Zmiana w {team.name}: {out_p.name} -> {in_p.name}")

    def _simulate_duel(self, minute: int, attacker: Team, defender: Team) -> None:
        # Wybierz losowych graczy (prosto)
        att = self._rng.choice(attacker.players) if attacker.players else None
        dff = self._rng.choice(defender.players) if defender.players else None
        if not att or not dff:
            return
        res = self.duels.resolve_random_duel(att, dff, attacker, defender)
        # zlicz total
        self.stats.duels_total_a += 1
        self.stats.duels_total_b += 1
        # policz duels_won_* jako zwycięstwo atakującego lub strzał
        win_att = (res.get("outcome") == "win") or (res.get("type") == "shot")
        if win_att:
            if attacker is self.team_a: self.stats.duels_won_a += 1
            else: self.stats.duels_won_b += 1
        # jeśli to strzał, zlicz do statystyk i ewentualnie gol
        if res.get("type") == "shot":
            on_target = bool(res.get("on_target"))
            if attacker is self.team_a:
                self.stats.shots_a += 1
                if on_target: self.stats.shots_on_a += 1
            else:
                self.stats.shots_b += 1
                if on_target: self.stats.shots_on_b += 1
            shot_outcome = res.get("shot_outcome")  # 'goal' | 'saved' | 'wide'
            if shot_outcome == "goal":
                scorer = getattr(att, 'name', 'Zawodnik')
                if attacker is self.team_a:
                    self.stats.goals_a.append((minute, scorer, None))
                else:
                    self.stats.goals_b.append((minute, scorer, None))
                self._add_event(minute, "goal", f"{minute}' - GOL! {attacker.name}! Strzelec: {scorer}")
            elif shot_outcome == "saved":
                self._add_event(minute, "shot_on_target", f"{minute}' - {getattr(att,'name','Zawodnik')} celnie — dobra interwencja bramkarza!")
            else:
                self._add_event(minute, "shot_off_target", f"{minute}' - {getattr(att,'name','Zawodnik')} niecelnie!")

    def _simulate_set_piece(self, minute: int, attacker: Team, defender: Team) -> None:
        r = self._rng.random()
        if r < 0.6:
            # rzut rożny
            if attacker is self.team_a: self.stats.corners_a += 1
            else: self.stats.corners_b += 1
            self._add_event(minute, "corner", f"{minute}' - Rzut rożny dla {attacker.name}!")
            # szansa na strzał po rogu
            if self._rng.random() < 0.35:
                self._simulate_duel(minute, attacker, defender)
        elif r < 0.95:
            # rzut wolny
            if attacker is self.team_a: self.stats.freekicks_a += 1
            else: self.stats.freekicks_b += 1
            # szansa na gol bezpośredni
            if self._rng.random() < 0.07:
                scorer = self._rng.choice(attacker.players).name if attacker.players else "Zawodnik"
                if attacker is self.team_a:
                    self.stats.goals_a.append((minute, scorer, None))
                else:
                    self.stats.goals_b.append((minute, scorer, None))
                self._add_event(minute, "goal_freekick", f"{minute}' - GOL! {attacker.name}! Strzelec: {scorer} (rzut wolny)")
            else:
                self._add_event(minute, "freekick", f"{minute}' - Rzut wolny dla {attacker.name}")
        else:
            # karny
            if attacker is self.team_a: self.stats.penalties_a += 1
            else: self.stats.penalties_b += 1
            self._add_event(minute, "penalty_awarded", f"{minute}' - Jest jedenastka dla {attacker.name}!")
            taker = self._rng.choice(attacker.players).name if attacker.players else "Zawodnik"
            if self._rng.random() < 0.78:
                if attacker is self.team_a:
                    self.stats.goals_a.append((minute, taker, None))
                else:
                    self.stats.goals_b.append((minute, taker, None))
                self._add_event(minute, "goal_penalty", f"{minute}' - GOL! {attacker.name}! Strzelec: {taker} (karny)")
            else:
                self._add_event(minute, "penalty_miss", f"{minute}' - Karny zmarnowany! {taker}")

    def _simulate_foul(self, minute: int, attacker: Team, defender: Team) -> None:
        # faul na korzyść atakującego; możliwa kartka dla obrony
        if defender is self.team_a: self.stats.fouls_a += 1
        else: self.stats.fouls_b += 1
        # żółta z małą szansą
        if self._rng.random() < 0.20:
            if defender is self.team_a: self.stats.yellows_a += 1
            else: self.stats.yellows_b += 1
            self._add_event(minute, "yellow", f"{minute}' - Żółta kartka dla zawodnika {defender.name}")
        # czerwona bardzo rzadko
        elif self._rng.random() < 0.03:
            if defender is self.team_a: self.stats.reds_a += 1
            else: self.stats.reds_b += 1
            self._add_event(minute, "red_card", f"{minute}' - Czerwona kartka dla zawodnika {defender.name}")

    def _build_report(self) -> Dict:
        def _compress_minute(m: int) -> int:
            return m
        timeline: List[Dict] = []
        for e in self._events:
            timeline.append({
                "minute": _compress_minute(int(e.get("minute", 1))),
                "team": "",
                "event_type": e.get("kind", "info"),
                "description": e.get("text", ""),
            })
        score_a = len(self.stats.goals_a)
        score_b = len(self.stats.goals_b)
        goals_combined = (
            [{"team": self.team_a.name, "minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_a]
            + [{"team": self.team_b.name, "minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_b]
        )
        # snapshot graczy (dystans z atrybutu distance_km jeśli jest, energia z obiektów)
        def build_player_stats(team: Team) -> List[Dict]:
            out: List[Dict] = []
            for p in team.players:
                out.append({
                    'id': getattr(p, 'id', 0),
                    'name': getattr(p, 'name', ''),
                    'position': getattr(p, 'position', ''),
                    'energy': round(getattr(p, 'energy', 1.0), 3),
                    'distance_km': round(float(getattr(p, 'distance_km', 0.0) or 0.0), 2),
                })
            return out
        pos_a = round(100 * self.possession_a_ticks / max(1, self.possession_a_ticks + self.possession_b_ticks), 1)
        pos_b = round(100 - pos_a, 1)
        return {
            "team_a": self.team_a.name,
            "team_b": self.team_b.name,
            "score": (score_a, score_b),
            "score_a": score_a,
            "score_b": score_b,
            "referee": self.referee,
            "possession": {self.team_a.name: pos_a, self.team_b.name: pos_b},
            "shots": {self.team_a.name: self.stats.shots_a, self.team_b.name: self.stats.shots_b},
            "shots_on_target": {self.team_a.name: self.stats.shots_on_a, self.team_b.name: self.stats.shots_on_b},
            "events": timeline,
            "events_full": timeline,
            "goals": goals_combined,
            "goals_a": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_a],
            "goals_b": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_b],
            "substitutions": [],
            "tactical_impact": {"team_a_style": getattr(self.team_a, 'style', 'balanced'), "team_b_style": getattr(self.team_b, 'style', 'balanced')},
            "stats": {
                "possession_a": pos_a, "possession_b": pos_b,
                "shots_a": self.stats.shots_a, "shots_on_a": self.stats.shots_on_a,
                "shots_b": self.stats.shots_b, "shots_on_b": self.stats.shots_on_b,
                "duels_won_a": self.stats.duels_won_a, "duels_won_b": self.stats.duels_won_b,
                "duels_total_a": self.stats.duels_total_a, "duels_total_b": self.stats.duels_total_b,
                "fouls_a": self.stats.fouls_a, "fouls_b": self.stats.fouls_b,
                "yellows_a": self.stats.yellows_a, "yellows_b": self.stats.yellows_b,
                "reds_a": self.stats.reds_a, "reds_b": self.stats.reds_b,
                "corners_a": self.stats.corners_a, "corners_b": self.stats.corners_b,
                "freekicks_a": self.stats.freekicks_a, "freekicks_b": self.stats.freekicks_b,
                "penalties_a": self.stats.penalties_a, "penalties_b": self.stats.penalties_b,
            },
            "player_stats": {
                self.team_a.name: build_player_stats(self.team_a),
                self.team_b.name: build_player_stats(self.team_b),
            },
        }
