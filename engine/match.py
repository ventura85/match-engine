from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
import copy as _copy
from typing import Dict, List, Tuple, Optional

from models.team import Team
from models.player import Player
from engine.fatigue import apply_fatigue_tick, FatigueContext, halftime_regen
from engine.injury import maybe_injury
from engine.duel import DuelSystem
from engine.comments_repo_mvp import CommentsRepoMVP
from engine.commentary import CommentaryComposer
from engine.comments import format_names

# Eksportowane stałe (używane w main.py)
TOTAL_SIM_MINUTES = 90
DEFAULT_REAL_MINUTES = 8

@dataclass
class MatchStats:
    shots_a: int = 0
    shots_on_a: int = 0
    shots_b: int = 0
    shots_on_b: int = 0
    # xG agregaty (prosty model raportowy)
    xg_a: float = 0.0
    xg_b: float = 0.0
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
        # Izoluj stan wejściowy – pracuj na głębokich kopiach drużyn
        self.team_a = _copy.deepcopy(team_a)
        self.team_b = _copy.deepcopy(team_b)
        self.verbose = verbose
        self.real_time = real_time
        self.real_minutes_target = max(2, min(30, int(real_minutes_target)))
        self.density = density
        self.stats = MatchStats()
        self.possession_a_ticks = 0
        self.possession_b_ticks = 0
        # Używamy globalnego RNG (deterministyczny po set_random_seed z engine.utils)
        self._rng = random
        self._events: List[Dict] = []
        # uproszczony sędzia (zgodne z main.py)
        prof = str(referee_profile or 'neutral').lower()
        if prof == 'lenient':
            ym, rm = 0.90, 0.90
        elif prof == 'strict':
            ym, rm = 1.15, 1.15
        else:
            ym, rm = 1.0, 1.0
        self.referee = {"key": prof, "label": prof.capitalize(), "foul_mult": 1.0, "yellow_mult": ym, "red_mult": rm}
        self.duels = DuelSystem()
        self.substitutions: List[Dict] = []
        # Licznik dostępnych zmian na zespół (na potrzeby testów)
        self._subs_left: Dict[str, int] = {self.team_a.name: 3, self.team_b.name: 3}
        # Flaga ostatniego wygranego pojedynku per team (do heurystyki xG)
        self._last_duel_win_minute: Dict[str, int] = {self.team_a.name: 0, self.team_b.name: 0}
        # Repo komentarzy (oddzielny RNG, by nie wpływać na przebieg symulacji)
        try:
            import random as _rnd
            self._comments = CommentsRepoMVP(lang='pl', pack='pl_fun')
            self._comments.rng = _rnd.Random(12345)
            self._comments.load()
            # Globalny cooldown komentarzy
            self._commentary = CommentaryComposer(repo=self._comments, global_cooldown=4)
        except Exception:
            self._comments = None
            self._commentary = None

    def _award_freekick(self, team: str, minute: int, reason: str | None = None) -> None:
        """
        Atomowo: emisja eventu przyznania wolnego + inkrement statystyk.

        Event: kind="freekick_awarded" z tagiem team oraz opisem.
        Stat: freekicks_a/b zwiększane dokładnie w tym miejscu.
        """
        if team == self.team_a.name:
            self.stats.freekicks_a += 1
        elif team == self.team_b.name:
            self.stats.freekicks_b += 1
        msg = f"{minute}' - Przyznany rzut wolny dla {team}!"
        if reason:
            msg += f" ({reason})"
        self._add_event(minute, "freekick_awarded", msg, team=team)

    def _add_event(self, minute: int, kind: str, text: str, team: str | None = "") -> None:
        self._events.append({"kind": kind, "text": text, "minute": minute, "team": team or ""})
        if self.verbose:
            print(text)

    def simulate_match(self) -> Dict:
        total_minutes = TOTAL_SIM_MINUTES
        # start
        self._add_event(0, "banner", f"Mecz: {self.team_a.name} vs {self.team_b.name}")
        # pętla minutowa (prosty model)
        # użyj _simulate_minute dla kompatybilności z testami
        for minute in range(1, 46):
            self._simulate_minute(1, minute)
        for minute in range(46, total_minutes + 1):
            if minute in (60, 75):
                self._maybe_substitution(minute, self.team_a)
                self._maybe_substitution(minute, self.team_b)
            self._simulate_minute(2, minute)
        self._add_event(90, "final_whistle", "Koniec meczu!")
        return self._build_report()

    # API kompatybilne z testami: pojedyncza minuta (half/minute)
    def _simulate_minute(self, half: int, minute: int) -> None:
        # delegacja do modułu minute_simulator
        try:
            from .minute_simulator import simulate_minute as _sim_min
            _sim_min(self, half, minute)
        except Exception:
            return

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
        self.substitutions.append({'minute': minute, 'team': team.name, 'out': out_p.name, 'in': in_p.name})

    # Wrappery kompatybilne z testami
    def _simulate_foul(self, half: int, minute: int, team_in_possession: Team) -> None:
        attacker = team_in_possession
        defender = self.team_b if attacker is self.team_a else self.team_a
        self._simulate_foul_internal(minute, attacker, defender)

    def _simulate_duel(self, half: int, minute: int, team_in_possession: Team) -> None:
        attacker = team_in_possession
        defender = self.team_b if attacker is self.team_a else self.team_a
        self._simulate_duel_internal(minute, attacker, defender)

    def _simulate_set_piece(self, half: int, minute: int, team_in_possession: Team) -> None:
        attacker = team_in_possession
        defender = self.team_b if attacker is self.team_a else self.team_a
        self._simulate_set_piece_internal(minute, attacker, defender)

    def _pick_defender(self, team: Team) -> Player:
        pool = [p for p in team.players if (getattr(p, 'position', '').upper() == 'DEF')]
        if not pool:
            pool = team.players or []
        return self._rng.choice(pool) if pool else Player(id=0, name='Obrońca', position='DEF', attributes={})

    def _pick_attacker(self, team: Team) -> Player:
        pool = [p for p in team.players if (getattr(p, 'position', '').upper() in ('FWD','MID'))]
        if not pool:
            pool = team.players or []
        return self._rng.choice(pool) if pool else Player(id=0, name='Napastnik', position='FWD', attributes={})

    def _simulate_duel_internal_new(self, minute: int, attacker: Team, defender: Team) -> None:
        # Wyznacz graczy biorących udział w pojedynku
        att = self._rng.choice(attacker.players) if attacker.players else None
        dff = self._rng.choice(defender.players) if defender.players else None
        if not att or not dff:
            return
        res = self.duels.resolve_random_duel(att, dff, attacker, defender)
        # zlicz total (pojedynczy pojedynek zwiększa łączną liczbę po obu stronach)
        self.stats.duels_total_a += 1
        self.stats.duels_total_b += 1
        # Zwycięzca pojedynku: strzał lub 'win' -> atakujący; 'lose' -> broniący
        if (res.get("type") == "shot") or (res.get("outcome") == "win"):
            if attacker is self.team_a:
                self.stats.duels_won_a += 1
                self._last_duel_win_minute[self.team_a.name] = minute
            else:
                self.stats.duels_won_b += 1
                self._last_duel_win_minute[self.team_b.name] = minute
        elif res.get("outcome") == "lose":
            if defender is self.team_a:
                self.stats.duels_won_a += 1
                self._last_duel_win_minute[self.team_a.name] = minute
            else:
                self.stats.duels_won_b += 1
                self._last_duel_win_minute[self.team_b.name] = minute
        # Strzał w wyniku pojedynku: statystyki + xG + ewentualny gol
        if res.get("type") == "shot":
            on_target = bool(res.get("on_target"))
            if attacker is self.team_a:
                self.stats.shots_a += 1
                if on_target:
                    self.stats.shots_on_a += 1
            else:
                self.stats.shots_b += 1
                if on_target:
                    self.stats.shots_on_b += 1
            # xG heurystyka
            base = 0.08
            if on_target:
                base += 0.06
            last_win = self._last_duel_win_minute.get(attacker.name, 0)
            if last_win and (minute - last_win) <= 10:
                base += 0.08
            if (minute % 5) == 0:
                base += 0.10
            shot_xg = max(0.02, min(0.40, base))
            if attacker is self.team_a:
                self.stats.xg_a += shot_xg
            else:
                self.stats.xg_b += shot_xg
            # outcome z komentarzem
            shot_outcome = res.get("shot_outcome")
            ctx = {
                'name': getattr(att, 'name', 'Zawodnik'),
                'att': getattr(att, 'name', 'Zawodnik'),
                'def': getattr(dff, 'name', 'Obrońca'),
                'team': attacker.name,
                'minute': minute,
            }
            if shot_outcome == "goal":
                scorer = getattr(att, 'name', 'Zawodnik')
                if attacker is self.team_a:
                    self.stats.goals_a.append((minute, scorer, None))
                else:
                    self.stats.goals_b.append((minute, scorer, None))
                self._emit_commentary(minute, 'goal', ctx, final_kind='goal')
            elif shot_outcome == "saved":
                self._emit_commentary(minute, 'shot_saved', ctx, final_kind='shot_on_target')
            else:
                self._emit_commentary(minute, 'shot_off', ctx, final_kind='shot_off_target')

    def _simulate_duel_internal(self, minute: int, attacker: Team, defender: Team) -> None:
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
                self._add_event(minute, "goal", f"{minute}' - GOL! {attacker.name}! Strzelec: {scorer}", team=attacker.name)
            elif shot_outcome == "saved":
                self._add_event(minute, "shot_on_target", f"{minute}' - {getattr(att,'name','Zawodnik')} celnie — dobra interwencja bramkarza!", team=attacker.name)
            else:
                self._add_event(minute, "shot_off_target", f"{minute}' - {getattr(att,'name','Zawodnik')} niecelnie!", team=attacker.name)

    def _simulate_set_piece_internal(self, minute: int, attacker: Team, defender: Team) -> None:
        r = self._rng.random()
        if r < 0.6:
            # rzut rożny
            if attacker is self.team_a: self.stats.corners_a += 1
            else: self.stats.corners_b += 1
            self._add_event(minute, "corner", f"{minute}' - Rzut rożny dla {attacker.name}!", team=attacker.name)
            # szansa na strzał po rogu
            if self._rng.random() < 0.35:
                self._simulate_duel_internal_new(minute, attacker, defender)
        elif r < 0.95:
            # rzut wolny — zliczaj TYLKO przy przyznaniu
            self._award_freekick(attacker.name, minute, reason="set_piece")
            # szansa na gol bezpośredni
            if self._rng.random() < 0.07:
                scorer = self._rng.choice(attacker.players).name if attacker.players else "Zawodnik"
                if attacker is self.team_a:
                    self.stats.goals_a.append((minute, scorer, None))
                else:
                    self.stats.goals_b.append((minute, scorer, None))
                self._add_event(minute, "goal", f"{minute}' - GOL! {attacker.name}! Strzelec: {scorer} (rzut wolny)", team=attacker.name)
            else:
                self._add_event(minute, "freekick", f"{minute}' - Rzut wolny dla {attacker.name}", team=attacker.name)
        else:
            # karny
            if attacker is self.team_a: self.stats.penalties_a += 1
            else: self.stats.penalties_b += 1
            self._add_event(minute, "penalty_awarded", f"{minute}' - Jest jedenastka dla {attacker.name}!", team=attacker.name)
            taker = self._rng.choice(attacker.players).name if attacker.players else "Zawodnik"
            if self._rng.random() < 0.78:
                if attacker is self.team_a:
                    self.stats.goals_a.append((minute, taker, None))
                else:
                    self.stats.goals_b.append((minute, taker, None))
                self._add_event(minute, "goal", f"{minute}' - GOL! {attacker.name}! Strzelec: {taker} (karny)", team=attacker.name)
            else:
                self._add_event(minute, "penalty_miss", f"{minute}' - Karny zmarnowany! {taker}", team=attacker.name)

    def _simulate_foul_internal(self, minute: int, attacker: Team, defender: Team) -> None:
        # zlicz faule
        if defender is self.team_a: self.stats.fouls_a += 1
        else: self.stats.fouls_b += 1
        # Przyznaj rzut wolny dla atakujących (awarded-only semantics)
        self._award_freekick(attacker.name, minute, reason="foul")
        # Deterministyczny wpis o wolnym (bez zależności od repo)
        self._add_event(minute, 'freekick', f"{minute}' - Rzut wolny dla {attacker.name}", team=attacker.name)
        # wybór „ukaranego” obrońcy
        booked_obj = self._pick_defender(defender)
        # mentalne wpływy
        def _mental(p: Player, key: str, default: float = 50.0) -> float:
            try:
                return float(((getattr(p, 'attributes', {}) or {}).get('mental', {}) or {}).get(key, default))
            except Exception:
                return default
        aggr = _mental(booked_obj, 'aggression', 50.0)
        decis = _mental(booked_obj, 'decisions', 60.0)
        def clamp01(x: float) -> float:
            return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
        p_dr = clamp01((DIRECT_RED_PROB + 0.01 * ((aggr - 50.0) / 50.0) - 0.005 * ((decis - 50.0) / 50.0)) * float(self.referee.get('red_mult', 1.0)))
        p_y = clamp01((YELLOW_PROB + 0.08 * ((aggr - 50.0) / 50.0) - 0.05 * ((decis - 50.0) / 50.0)) * float(self.referee.get('yellow_mult', 1.0)))
        # checki w kolejności: foul_place_box (nieistotne tu), direct red, yellow
        _ = self._rng.random()  # foul_place_box placeholder, zgodnie z oczekiwaniami testów
        if self._rng.random() < p_dr:
            if defender is self.team_a: self.stats.reds_a += 1
            else: self.stats.reds_b += 1
            self._add_event(minute, "red_card", f"{minute}' - Czerwona kartka dla {booked_obj.name}", team=defender.name)
            return
        if self._rng.random() < p_y:
            if defender is self.team_a: self.stats.yellows_a += 1
            else: self.stats.yellows_b += 1
            self._add_event(minute, "yellow", f"{minute}' - Żółta kartka dla {booked_obj.name}", team=defender.name)

    def _emit_commentary(self, minute: int, outcome_key: str, context: Dict[str, str], final_kind: str) -> None:
        repo = getattr(self, '_comments', None)
        # Buildup: 1 linia z 'announce' (deterministycznie)
        if repo is not None:
            try:
                # Jeżeli dostępny globalny kompozytor komentarzy – użyj go
                picker = getattr(self, '_commentary', None) or repo
                txt = picker.pick('announce', **context) or ''
                txt = format_names(txt, context)
                if txt:
                    self._add_event(minute, 'micro', f"{minute}' - {txt}", team=context.get('team',''))
            except Exception:
                pass
        else:
            # bez repo nie emitujemy buildupu (komentarze tylko z repo)
            pass
        # Outcome line
        outcome_txt = ''
        if repo is not None:
            try:
                picker = getattr(self, '_commentary', None) or repo
                outcome_txt = picker.pick(outcome_key, **context) or ''
            except Exception:
                outcome_txt = ''
        if not outcome_txt:
            # Fallbacki, jeśli brak klucza w paczce – deterministyczne (bez globalnego RNG)
            if outcome_key == 'corner':
                outcome_txt = f"Rzut rożny dla {context.get('team','')}!"
            elif outcome_key == 'freekick':
                outcome_txt = "Rzut wolny."
        outcome_txt = format_names(outcome_txt, context)
        self._add_event(minute, final_kind, f"{minute}' - {outcome_txt}", team=context.get('team',''))

    def _build_report(self) -> Dict:
        def _compress_minute(m: int) -> int:
            # mapuj 1..90 -> 1..10, pomijaj 0
            if m < 1:
                return 1
            return min(10, int((m - 1) * 10 / TOTAL_SIM_MINUTES) + 1)
        timeline_all: List[Dict] = []
        for e in self._events:
            kind = e.get("kind", "info")
            minute0 = int(e.get("minute", 1))
            desc = e.get("text", "")
            # Wymóg: komentarze z repo – podmień treść dla wybranych rodzajów
            try:
                repo = getattr(self, '_comments', None)
                if repo is not None:
                    key_map = {
                        'corner': 'corner_wasted',
                        'freekick': 'freekick',
                    }
                    k = key_map.get(kind)
                    if k:
                        picker = getattr(self, '_commentary', None) or repo
                        txt = picker.pick(k, minute=minute0, team='') or ''
                        txt = format_names(txt, {'team': '', 'minute': minute0})
                        if txt:
                            desc = f"{minute0}' - {txt}"
            except Exception:
                pass
            timeline_all.append({
                "minute": _compress_minute(minute0),
                "team": e.get("team", ""),
                "event_type": kind,
                "description": desc,
            })
        # W raporcie 'events' pomijamy mikro-linie, pełny zapis w 'events_full'
        timeline = [ev for ev in timeline_all if ev["event_type"] != "micro"]
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
            "events_full": timeline_all,
            "goals": goals_combined,
            "goals_a": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_a],
            "goals_b": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_b],
            "substitutions": list(self.substitutions),
            "tactical_impact": {"team_a_style": getattr(self.team_a, 'style', 'balanced'), "team_b_style": getattr(self.team_b, 'style', 'balanced')},
            "stats": {
                "possession_a": pos_a, "possession_b": pos_b,
                "shots_a": self.stats.shots_a, "shots_on_target_a": self.stats.shots_on_a,
                "shots_b": self.stats.shots_b, "shots_on_target_b": self.stats.shots_on_b,
                "xg_a": round(self.stats.xg_a, 2), "xg_b": round(self.stats.xg_b, 2),
                "duels_won_a": self.stats.duels_won_a, "duels_won_b": self.stats.duels_won_b,
                "duels_total_a": self.stats.duels_total_a, "duels_total_b": self.stats.duels_total_b,
                "fouls_a": self.stats.fouls_a, "fouls_b": self.stats.fouls_b,
                "yellows_a": self.stats.yellows_a, "yellows_b": self.stats.yellows_b,
                "reds_a": self.stats.reds_a, "reds_b": self.stats.reds_b,
                "corners_a": self.stats.corners_a, "corners_b": self.stats.corners_b,
                "freekicks_a": self.stats.freekicks_a, "freekicks_b": self.stats.freekicks_b,
                "penalties_a": self.stats.penalties_a, "penalties_b": self.stats.penalties_b,
            },
            "xg_a": round(self.stats.xg_a, 2),
            "xg_b": round(self.stats.xg_b, 2),
            "player_stats": {
                self.team_a.name: build_player_stats(self.team_a),
                self.team_b.name: build_player_stats(self.team_b),
            },
        }
# Prawdopodobieństwa kar dla testów agresji/sędziego
YELLOW_PROB = 0.27
SECOND_YELLOW_TO_RED_PROB = 0.25
DIRECT_RED_PROB = 0.03




