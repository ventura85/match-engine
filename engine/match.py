from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from models.team import Team
from models.player import Player
from engine.duel import DuelSystem
from engine.utils import calculate_team_strength
from engine.comments import Commentary as C
from engine.comments_adapter import Comments as CA
import copy

# Tempo: 90 minut gry (generowane natychmiast). Real-time możliwy w przyszłości.
DEFAULT_REAL_MINUTES = 20
TOTAL_SIM_MINUTES = 90
HALF_SIM_MINUTES = 45

# Parametry zdarzeń (kalibracja v1)
BASE_SHOT_PROB = 0.165
STYLE_ATK_SHOT_BONUS = 0.035
STYLE_DEF_SHOT_MALUS = 0.025
WINGS_SHOT_BONUS = 0.012

SAVE_TO_CORNER_PROB = 0.30
BLOCK_TO_CORNER_PROB = 0.22

FOUL_PROB_PER_MIN = 0.16
STYLE_DEF_FOUL_BONUS = 0.03
YELLOW_PROB = 0.27
SECOND_YELLOW_TO_RED_PROB = 0.25
DIRECT_RED_PROB = 0.03

FREEKICK_GOAL_BASE = 0.07
PENALTY_PROB = 0.15
PENALTY_GOAL = 0.76

DUELS_PER_HALF = 3
BUFF_PERCENT = 0.10
BUFF_DURATION_MIN = 20
RESTORE_ENERGY = 0.20

# Density (bez 'ultra')
DENSITY_LEVELS = {
    "low":  {"micro_prob": 0.35, "micro_min": 0, "micro_max": 1},
    "med":  {"micro_prob": 0.60, "micro_min": 0, "micro_max": 2},
    "high": {"micro_prob": 0.85, "micro_min": 1, "micro_max": 2}
}

# Profile sędziego – wpływa na faule i kartki (mnożniki)
REFEREE_PROFILES = [
    {
        "key": "lenient", "label": "Łagodny",
        "foul_mult": 0.95, "yellow_mult": 0.90, "red_mult": 0.90, "weight": 0.35,
    },
    {
        "key": "neutral", "label": "Neutralny",
        "foul_mult": 1.00, "yellow_mult": 1.00, "red_mult": 1.00, "weight": 0.45,
    },
    {
        "key": "strict", "label": "Surowy",
        "foul_mult": 1.05, "yellow_mult": 1.15, "red_mult": 1.15, "weight": 0.20,
    },
]

@dataclass
class MatchStats:
    shots_a: int = 0
    shots_on_a: int = 0
    shots_b: int = 0
    shots_on_b: int = 0
    pos_a_ticks: int = 0
    pos_b_ticks: int = 0
    duels_won_a: int = 0
    duels_won_b: int = 0

    fouls_a: int = 0
    fouls_b: int = 0
    yellows_a: int = 0
    yellows_b: int = 0
    reds_a: int = 0
    reds_b: int = 0

    corners_a: int = 0
    corners_b: int = 0
    freekicks_a: int = 0
    freekicks_b: int = 0
    penalties_a: int = 0
    penalties_b: int = 0

    goals_a: List[Tuple[int, str, Optional[str]]] = field(default_factory=list)
    goals_b: List[Tuple[int, str, Optional[str]]] = field(default_factory=list)

class MatchEngine:
    def __init__(
        self,
        team_a: Team,
        team_b: Team,
        verbose: bool = False,
        real_time: bool = False,
        real_minutes_target: int = DEFAULT_REAL_MINUTES,
        density: str = "high",  # domyślnie high dla MMO, ale bez „ultra”
        referee_profile: str | None = None,
    ) -> None:
        # Pracujemy na kopiach, aby nie mutować wejścia i zapewnić deterministykę testów
        def _clone_team(src: Team) -> Team:
            t = copy.deepcopy(src)
            # Ustandaryzuj energię startową (testy zakładają deterministyczny start)
            for p in getattr(t, 'players', []) or []:
                try:
                    p.energy = 1.0
                except Exception:
                    pass
            return t
        self.team_a = _clone_team(team_a)
        self.team_b = _clone_team(team_b)
        self.verbose = verbose

        # Zachowaj style wejściowe do raportu taktycznego (nie nadpisywać zmianami w trakcie meczu)
        self._initial_tactics = {
            'team_a_style': getattr(self.team_a, 'style', 'balanced'),
            'team_b_style': getattr(self.team_b, 'style', 'balanced'),
        }

        self.real_time = bool(real_time)
        self.real_minutes_target = max(1, int(real_minutes_target))
        self.seconds_per_sim_minute = (self.real_minutes_target * 60.0) / TOTAL_SIM_MINUTES

        self.strength_a = calculate_team_strength(self.team_a)
        self.strength_b = calculate_team_strength(self.team_b)

        self.events: List[Dict] = []
        self.stats = MatchStats()
        self.duel = DuelSystem()
        # Komentarze makro (dłuższe, rzadsze)
        self.cadv = CA()
        # Reset komentarzy klasowych (anti‑repeat) dla deterministyki między uruchomieniami
        try:
            C.load()
        except Exception:
            pass

        self.duel_minutes_h1 = self._pick_duel_minutes(half=1, count=DUELS_PER_HALF)
        self.duel_minutes_h2 = self._pick_duel_minutes(half=2, count=DUELS_PER_HALF)

        self.cards_yellow_a: Dict[str, int] = {}
        self.cards_yellow_b: Dict[str, int] = {}
        self.buff_until: Dict[str, int] = {}

        self._h2_stoppages = 0.0

        # density config
        self.density = density if density in DENSITY_LEVELS else "high"
        self._dconf = DENSITY_LEVELS[self.density]

        # BLOKADA: max 1 gol w danej minucie, niezależnie od ścieżki (akcja/SFG/pojedynki)
        self._minute_goal_lock: set[int] = set()
        # Makro‑narracje: cele i harmonogram
        self._macro_emitted = 0
        self._macro_target = {"low": 2, "med": 3, "high": 4}.get(self.density, 3)
        self._macro_next = 2

        # Aktywni zawodnicy (pierwsza jedenastka) i zmiany
        self._active_idx: Dict[str, set[int]] = {
            self.team_a.name: set(range(min(11, len(self.team_a.players)))),
            self.team_b.name: set(range(min(11, len(self.team_b.players)))),
        }
        self._subs_left: Dict[str, int] = {self.team_a.name: 3, self.team_b.name: 3}
        self.substitutions: List[Dict] = []

        # Sędzia – wybór profilu (losowy lub wymuszony). Domyślnie neutralny
        # (testy deterministyczne). CLI może przekazać "random".
        self.referee = self._pick_referee(referee_profile)

        # Obciążenie / dystans i kontrola zmęczenia
        self._p_load: Dict[tuple, float] = {}
        self._fatigue_last_minute: int = -1

    def _pick_referee(self, key: str | None) -> Dict:
        # Wybór z predefiniowanych profili
        profs = REFEREE_PROFILES
        keys = {p.get('key'): p for p in profs}
        if key in keys:
            return dict(keys[key])
        if key == 'random':
            try:
                import random as _r
                weights = [float(p.get('weight', 1.0)) for p in profs]
                idx = _r.choices(range(len(profs)), weights=weights, k=1)[0]
                return dict(profs[idx])
            except Exception:
                return dict(keys.get('neutral', profs[1]))
        # domyślnie neutralny (deterministycznie)
        return dict(keys.get('neutral', profs[1]))

    # API
    def simulate_match(self) -> Dict:
        self._log_banner(f"🏟️  ROZPOCZĘCIE MECZU: {self.team_a.name} vs {self.team_b.name}")

        self._log_line("⏱️  PIERWSZA POŁOWA")
        for minute in range(1, HALF_SIM_MINUTES + 1):
            self._simulate_minute(half=1, minute=minute)
            if self.real_time:
                time.sleep(self.seconds_per_sim_minute)

        self._half_time_adjustments()
        self._log_line("")
        self._log_banner(
            f"⏸️  PRZERWA - Wynik: {self.team_a.name} {len(self.stats.goals_a)}:{len(self.stats.goals_b)} {self.team_b.name}"
        )

        self._log_line("⏱️  DRUGA POŁOWA")
        for minute in range(HALF_SIM_MINUTES + 1, TOTAL_SIM_MINUTES + 1):
            self._simulate_minute(half=2, minute=minute)
            if self.real_time:
                time.sleep(self.seconds_per_sim_minute)

        added = self._compute_stoppage_time()
        self._add_event(90, "", "stoppage_time", C.stoppage(added))
        if self.verbose:
            print(C.stoppage(added))

        if added > 0:
            for minute in range(91, 90 + added + 1):
                self._simulate_minute(half=2, minute=minute)
                if self.real_time:
                    time.sleep(self.seconds_per_sim_minute)

        self._log_banner("🏁 KONIEC MECZU!")
        # można dodać final_whistle jako event, ale raport i tak zawiera koniec meczu
        if self.verbose:
            print(C.final_whistle())
        return self._generate_report()

    # minuta meczu
    def _simulate_minute(self, half: int, minute: int) -> None:
        # Zmiany personalne i taktyczne w kluczowych minutach
        if half == 2 and minute in (60, 75):
            self._attempt_substitutions(minute)
        if half == 2 and minute == 70:
            self._maybe_tactical_change_in_play(minute)
        ctrl_a = self.strength_a["control"] * self._style_control_factor(self.team_a.style) * self._control_modifier(self.team_a)
        ctrl_b = self.strength_b["control"] * self._style_control_factor(self.team_b.style) * self._control_modifier(self.team_b)
        team_in_possession = self.team_a if (random.random() < (ctrl_a / max(0.0001, ctrl_a + ctrl_b))) else self.team_b
        defending_team = self.team_b if team_in_possession is self.team_a else self.team_a

        if team_in_possession is self.team_a:
            self.stats.pos_a_ticks += 1
        else:
            self.stats.pos_b_ticks += 1

        # kolejność: duel -> foul/SFG -> akcja
        if (half == 1 and minute in self.duel_minutes_h1) or (half == 2 and minute in self.duel_minutes_h2):
            self._simulate_duel(half, minute, team_in_possession)
            self._maybe_micro(minute, team_in_possession, defending_team)
            self._maybe_macro(minute, team_in_possession, defending_team)
            return

        if self._minute_foul_occurs(team_in_possession):
            self._simulate_foul(half, minute, team_in_possession)
            self._maybe_micro(minute, team_in_possession, defending_team)
            self._maybe_macro(minute, team_in_possession, defending_team)
            return

        self._simulate_action(half, minute, team_in_possession)
        self._maybe_micro(minute, team_in_possession, defending_team)
        self._maybe_macro(minute, team_in_possession, defending_team)

    def _simulate_action(self, half: int, minute: int, attacking_team: Team) -> None:
        defending_team = self.team_b if attacking_team is self.team_a else self.team_a
        atk = self._team_attack_value(attacking_team, minute)
        defv = self._team_defense_value(defending_team, minute)

        p_shot = self._prob_shot(attacking_team, defending_team)
        p_on = self._prob_shot_on_target(atk, defv)

        if random.random() < p_shot:
            shooter = self._pick_attacker(attacking_team)
            on_target = (random.random() < p_on)

            if attacking_team is self.team_a:
                self.stats.shots_a += 1
                if on_target: self.stats.shots_on_a += 1
            else:
                self.stats.shots_b += 1
                if on_target: self.stats.shots_on_b += 1

            gk_overall = self._keeper_overall(defending_team)
            shoot_power = atk * random.uniform(0.85, 1.15)
            goal_prob = self._prob_goal(shoot_power, gk_overall)

            if on_target and (random.random() < goal_prob) and (minute not in self._minute_goal_lock):
                assist = self._maybe_assist(attacking_team, prefer=shooter)
                self._score_goal(half, minute, attacking_team, shooter.name, assist, context=None)
                self._minute_goal_lock.add(minute)
                if minute > HALF_SIM_MINUTES:
                    self._h2_stoppages += 1.0
            else:
                if on_target:
                    corner_factor = 0.6 if getattr(self, "_prev_event_type", None) == "corner" and getattr(self, "_prev_event_min", -1) == minute else 1.0
                    if random.random() < (SAVE_TO_CORNER_PROB * corner_factor):
                        self._register_corner(minute, attacking_team, text=C.corner_parried(shooter, attacking_team, defending_team))
                    else:
                        self._add_event(minute, attacking_team.name, "shot_on_target",
                                        f"{minute}' - 🧤 {C.shot_on_target(shooter, attacking_team, defending_team)}")
                else:
                    corner_factor = 0.6 if getattr(self, "_prev_event_type", None) == "corner" and getattr(self, "_prev_event_min", -1) == minute else 1.0
                    if random.random() < (BLOCK_TO_CORNER_PROB * corner_factor):
                        self._register_corner(minute, attacking_team, text=C.corner_blocked(shooter, attacking_team, defending_team))
                    else:
                        self._add_event(minute, attacking_team.name, "shot_off_target",
                                        f"{minute}' - ❌ {C.shot_off_target(shooter, attacking_team)}")
        else:
            if random.random() < 0.5:
                text = C.build_up_short(attacking_team, defending_team)
            else:
                text = C.build_up_medium(attacking_team, defending_team)
            self._add_event(minute, attacking_team.name, "build_up", f"{minute}' - {text}")
        # Zastosuj zmęczenie po minucie akcji
        self._apply_minute_fatigue(minute, attacking_team, defending_team, None, None)

    def _simulate_duel(self, half: int, minute: int, attacking_team: Team) -> None:
        defending_team = self.team_b if attacking_team is self.team_a else self.team_a
        att_player = self._pick_attacker(attacking_team)
        def_player = self._pick_defender(defending_team)

        result = self.duel.resolve_random_duel(att_player, def_player, attacking_team, defending_team)

        if attacking_team is self.team_a:
            if result.get("outcome") == "win": self.stats.duels_won_a += 1
            elif result.get("outcome") == "lose": self.stats.duels_won_b += 1
        else:
            if result.get("outcome") == "win": self.stats.duels_won_b += 1
            elif result.get("outcome") == "lose": self.stats.duels_won_a += 1

        if result.get("type") == "shot" and result.get("outcome") != "lose":
            # Zlicz statystyki zgodnie z outcome duelu
            if attacking_team is self.team_a:
                self.stats.shots_a += 1
                if result.get("on_target"):
                    self.stats.shots_on_a += 1
            else:
                self.stats.shots_b += 1
                if result.get("on_target"):
                    self.stats.shots_on_b += 1

            shot_outcome = result.get("shot_outcome")  # 'goal' | 'saved' | 'wide'
            if shot_outcome == "goal" and (minute not in self._minute_goal_lock):
                assist = self._maybe_assist(attacking_team, prefer=att_player)
                self._score_goal(half, minute, attacking_team, att_player.name, assist if assist else None, context=None)
                self._add_event(minute, attacking_team.name, "context",
                                f"{minute}' - {C.duel_context(att_player, def_player)}")
                self._minute_goal_lock.add(minute)
                if minute > HALF_SIM_MINUTES:
                    self._h2_stoppages += 1.0
                # zmęczenie po pojedynku
                self._apply_minute_fatigue(minute, attacking_team, defending_team, att_player, def_player)
                return
            elif shot_outcome == "saved":
                if random.random() < SAVE_TO_CORNER_PROB:
                    self._register_corner(minute, attacking_team, text="Bramkarz z trudem wybija po pojedynku – rzut rożny!")
                else:
                    self._add_event(minute, attacking_team.name, "shot_on_target",
                                    f"{minute}' - 🧤 {C.duel_shot_saved(att_player)}")
                # zmęczenie po pojedynku
                self._apply_minute_fatigue(minute, attacking_team, defending_team, att_player, def_player)
                return
            else:  # wide
                self._add_event(minute, attacking_team.name, "shot_off_target",
                                f"{minute}' - ❌ {C.shot_off_target(att_player, attacking_team)}")
                # zmęczenie po pojedynku
                self._apply_minute_fatigue(minute, attacking_team, defending_team, att_player, def_player)
                return

        self._add_event(minute, attacking_team.name, f"duel_{result.get('type','action')}",
                        f"{minute}' - ⚔️ {result.get('detail','Zacięta walka o piłkę...')}")
        self._apply_minute_fatigue(minute, attacking_team, defending_team, att_player, def_player)

    # MICRO-EVENTY (tanie: nie zmieniają statystyk)
    def _maybe_micro(self, minute: int, att: Team, defe: Team) -> None:
        cfg = self._dconf
        if random.random() > cfg["micro_prob"]:
            return
        count = random.randint(cfg["micro_min"], cfg["micro_max"])
        if count <= 0:
            return
        used: set[str] = set()
        options = [
            ("pass", lambda: C.micro_pass_chain(att, defe)),
            ("press", lambda: C.micro_press(att, defe)),
            ("throw", lambda: C.micro_throw_in(att)),
            ("gk", lambda: C.micro_goal_kick(defe)),
            ("clear", lambda: C.micro_clearance(att, defe)),
        ]
        for _ in range(count):
            avail = [o for o in options if o[0] not in used]
            if not avail:
                break
            key, fn = random.choice(avail)
            used.add(key)
            txt = fn()
            self._add_event(minute, att.name, "micro", f"{minute}' - {txt}")

    # Makro‑narracje (rzadziej, dłuższe wpisy)
    def _maybe_macro(self, minute: int, att: Team, defe: Team) -> None:
        if self._macro_emitted >= self._macro_target:
            return
        if minute < self._macro_next:
            return
        # Heurystyki wyboru rodzaju narracji
        if minute in (HALF_SIM_MINUTES - 1, HALF_SIM_MINUTES, TOTAL_SIM_MINUTES - 1, TOTAL_SIM_MINUTES):
            kind = "endgame"
        else:
            r = random.random()
            if r < 0.35:
                kind = "pressure"
            elif r < 0.65:
                kind = "momentum"
            elif r < 0.85:
                kind = "macro_build"
            else:
                kind = "calm"
        text = self.cadv.macro(kind, team=att.name, minute=str(minute))
        self._add_event(minute, att.name, "narration", f"{minute}' - {text}")
        self._macro_emitted += 1
        # Zaplanuj następną narrację za 2–3 minuty
        self._macro_next = minute + random.randint(2, 3)

    # Faule / SFG / kartki
    def _minute_foul_occurs(self, attacking_team: Team) -> bool:
        defending = self.team_b if attacking_team is self.team_a else self.team_a
        p = FOUL_PROB_PER_MIN + (STYLE_DEF_FOUL_BONUS if (defending.style or '').lower() == 'defensive' else 0.0)
        # Pressing modyfikuje bazę
        try:
            p_def = defending.pressing_level()
        except Exception:
            p_def = 0
        if p_def > 0:
            p += 0.02
        elif p_def < 0:
            p -= 0.015
        # Agresja obrońców/midów lekkim czynnikiem
        avg_aggr = self._avg_aggression(defending)
        agg_delta = (avg_aggr - 50.0) / 50.0  # [-1, +1]
        p += 0.012 * agg_delta
        # Mnożnik sędziego
        try:
            p *= float(self.referee.get('foul_mult', 1.0))
        except Exception:
            pass
        return random.random() < max(0.0, min(0.35, p))

    def _simulate_foul(self, half: int, minute: int, attacking_team: Team) -> None:
        defending_team = self.team_b if attacking_team is self.team_a else self.team_a

        if attacking_team is self.team_a: self.stats.fouls_b += 1
        else: self.stats.fouls_a += 1

        if minute > HALF_SIM_MINUTES:
            self._h2_stoppages += 0.5

        foul_place_box = (random.random() < 0.22)
        booked_obj = self._pick_defender(defending_team)
        booked_player = booked_obj.name
        card_txt = ""

        # kartki – zależne od agresji i decyzji ukaranego
        aggr = self._mental_attr(booked_obj, 'aggression', 50.0)
        decis = self._mental_attr(booked_obj, 'decisions', 60.0)
        def clamp01(x: float) -> float:
            return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
        p_dr = clamp01(DIRECT_RED_PROB + 0.01 * ((aggr - 50.0) / 50.0) - 0.005 * ((decis - 50.0) / 50.0))
        p_y = clamp01(YELLOW_PROB + 0.08 * ((aggr - 50.0) / 50.0) - 0.05 * ((decis - 50.0) / 50.0))
        # Mnożniki sędziego
        try:
            y_mult = float(self.referee.get('yellow_mult', 1.0))
            r_mult = float(self.referee.get('red_mult', 1.0))
            p_y = clamp01(p_y * y_mult)
            p_dr = clamp01(p_dr * r_mult)
        except Exception:
            pass

        if random.random() < p_dr:
            self._give_red(minute, defending_team, booked_player)
            card_txt = f" {C.red_card(booked_player)}"
            if minute > HALF_SIM_MINUTES:
                self._h2_stoppages += 0.7
        else:
            if random.random() < p_y:
                is_second = self._give_yellow(defending_team, booked_player)
                if is_second and (random.random() < SECOND_YELLOW_TO_RED_PROB):
                    self._give_red(minute, defending_team, booked_player)
                    card_txt = f" 🟨🟨→ {C.red_card(booked_player)}"
                    if minute > HALF_SIM_MINUTES:
                        self._h2_stoppages += 0.7
                else:
                    card_txt = f" {C.yellow(booked_player)}"
                    if minute > HALF_SIM_MINUTES:
                        self._h2_stoppages += 0.3

        # SFG (JEDEN wpis przy golu)
        if foul_place_box and (random.random() < PENALTY_PROB):
            # karny
            self._register_penalty(minute, attacking_team)
            if minute > HALF_SIM_MINUTES:
                self._h2_stoppages += 0.6
            if (random.random() < PENALTY_GOAL) and (minute not in self._minute_goal_lock):
                scorer = self._pick_attacker(attacking_team).name
                self._score_goal(half, minute, attacking_team, scorer, None, context="penalty", extra_txt=card_txt)
                self._minute_goal_lock.add(minute)
                if minute > HALF_SIM_MINUTES:
                    self._h2_stoppages += 0.6
            else:
                self._add_event(minute, attacking_team.name, "penalty_miss",
                                f"{minute}' - ❌ {C.penalty_miss(attacking_team)}{card_txt}")
        else:
            # rzut wolny
            self._register_freekick(minute, attacking_team)
            if minute > HALF_SIM_MINUTES:
                self._h2_stoppages += 0.3
            if (random.random() < FREEKICK_GOAL_BASE) and (minute not in self._minute_goal_lock):
                scorer = self._pick_attacker(attacking_team).name
                self._score_goal(half, minute, attacking_team, scorer, None, context="freekick", extra_txt=card_txt)
                self._minute_goal_lock.add(minute)
                if minute > HALF_SIM_MINUTES:
                    self._h2_stoppages += 0.5
            else:
                self._add_event(minute, attacking_team.name, "freekick",
                                f"{minute}' - {C.freekick(attacking_team)}{card_txt}")
        # zmęczenie po minucie faulu/SFG
        self._apply_minute_fatigue(minute, attacking_team, defending_team, None, None)

    # Rejestry SFG
    def _register_corner(self, minute: int, team: Team, text: str) -> None:
        if team is self.team_a: self.stats.corners_a += 1
        else: self.stats.corners_b += 1
        self._add_event(minute, team.name, "corner", f"{minute}' - 🏳️ Rzut rożny dla {team.name}! {text}")
        if minute > HALF_SIM_MINUTES:
            self._h2_stoppages += 0.2

    def _register_freekick(self, minute: int, team: Team) -> None:
        if team is self.team_a: self.stats.freekicks_a += 1
        else: self.stats.freekicks_b += 1

    def _register_penalty(self, minute: int, team: Team) -> None:
        if team is self.team_a: self.stats.penalties_a += 1
        else: self.stats.penalties_b += 1

    # Kartki
    def _give_yellow(self, team: Team, player_name: str) -> bool:
        book = self.cards_yellow_a if team is self.team_a else self.cards_yellow_b
        book[player_name] = book.get(player_name, 0) + 1
        if team is self.team_a: self.stats.yellows_a += 1
        else: self.stats.yellows_b += 1
        return book[player_name] >= 2

    def _give_red(self, minute: int, team: Team, player_name: str) -> None:
        if team is self.team_a: self.stats.reds_a += 1
        else: self.stats.reds_b += 1
        self._add_event(minute, team.name, "red_card", f"{minute}' - {C.red_card(player_name)}")

    # Raport / zapis gola
    def _score_goal(
        self,
        half: int,
        minute: int,
        team: Team,
        scorer: str,
        assist: Optional[str],
        context: Optional[str] = None,
        extra_txt: str = ""
    ) -> None:
        """Zapisuje bramkę i dodaje JEDEN wpis narracyjny.
        context: None | 'penalty' | 'freekick'
        """
        if team is self.team_a:
            self.stats.goals_a.append((minute, scorer, assist))
        else:
            self.stats.goals_b.append((minute, scorer, assist))

        assist_txt = f" (asysta: {assist})" if assist else ""
        if context == "penalty":
            desc = f"{minute}' - ⚽ GOL! {team.name}! Strzelec: {scorer}{assist_txt} — {C.penalty_goal(scorer, team)}{extra_txt}"
            self._add_event(minute, team.name, "goal", desc)
        elif context == "freekick":
            desc = f"{minute}' - ⚽ GOL! {team.name}! Strzelec: {scorer}{assist_txt} — {C.freekick_goal(scorer, team)}{extra_txt}"
            self._add_event(minute, team.name, "goal", desc)
        else:
            self._add_event(minute, team.name, "goal", f"{minute}' - ⚽ GOL! {team.name}! Strzelec: {scorer}{assist_txt}")

    def _generate_report(self) -> Dict:
        total_ticks = max(1, self.stats.pos_a_ticks + self.stats.pos_b_ticks)
        pos_a = round(100.0 * self.stats.pos_a_ticks / total_ticks, 1)
        pos_b = round(100.0 * self.stats.pos_b_ticks / total_ticks, 1)

        # Pełen timeline 1..90+ do CLI
        events_full = [e for e in self.events if int(e.get("minute", 0)) >= 1]
        # Kompresja 1..90 -> 1..10 dla testów (report['events'])
        def _compress_minute(m: int) -> int:
            if m < 1:
                return 1
            return min(10, int((m - 1) * 10 / 90) + 1)
        timeline = []
        for e in events_full:
            ee = dict(e)
            ee["minute"] = _compress_minute(int(e.get("minute", 1)))
            timeline.append(ee)

        score_a = len(self.stats.goals_a)
        score_b = len(self.stats.goals_b)
        goals_combined = (
            [{"team": self.team_a.name, "minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_a]
            + [{"team": self.team_b.name, "minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_b]
        )

        # Player distance/energy snapshot
        def build_player_stats(team: Team) -> List[Dict]:
            out: List[Dict] = []
            for p in team.players:
                key = (team.name, getattr(p, 'id', p.name))
                load = self._p_load.get(key, 0.0)
                # Skala wyświetlania dystansu: 0.10 ~= 10–12 km dla intensywnych MID
                dist = round(0.10 * load, 2)
                out.append({
                    'id': getattr(p, 'id', 0),
                    'name': getattr(p, 'name', ''),
                    'position': getattr(p, 'position', ''),
                    'energy': round(getattr(p, 'energy', 1.0), 3),
                    'distance_km': dist,
                })
            return out

        return {
            "team_a": self.team_a.name,
            "team_b": self.team_b.name,
            "score": (score_a, score_b),
            "referee": {
                "key": self.referee.get('key', 'neutral'),
                "label": self.referee.get('label', 'Neutralny'),
                "foul_mult": self.referee.get('foul_mult', 1.0),
                "yellow_mult": self.referee.get('yellow_mult', 1.0),
                "red_mult": self.referee.get('red_mult', 1.0),
            },
            "possession": {self.team_a.name: pos_a, self.team_b.name: pos_b},
            "shots": {self.team_a.name: self.stats.shots_a, self.team_b.name: self.stats.shots_b},
            "shots_on_target": {self.team_a.name: self.stats.shots_on_a, self.team_b.name: self.stats.shots_on_b},
            "events": timeline,
            "events_full": events_full,
            "goals": goals_combined,
            "substitutions": list(self.substitutions),
            "tactical_impact": dict(self._initial_tactics),
            # Rich stats (zachowane do UI)
            "stats": {
                "possession_a": pos_a, "possession_b": pos_b,
                "shots_a": self.stats.shots_a, "shots_on_a": self.stats.shots_on_a,
                "shots_b": self.stats.shots_b, "shots_on_b": self.stats.shots_on_b,
                "duels_won_a": self.stats.duels_won_a, "duels_won_b": self.stats.duels_won_b,
                "fouls_a": self.stats.fouls_a, "fouls_b": self.stats.fouls_b,
                "yellows_a": self.stats.yellows_a, "yellows_b": self.stats.yellows_b,
                "reds_a": self.stats.reds_a, "reds_b": self.stats.reds_b,
                "corners_a": self.stats.corners_a, "corners_b": self.stats.corners_b,
                "freekicks_a": self.stats.freekicks_a, "freekicks_b": self.stats.freekicks_b,
                "penalties_a": self.stats.penalties_a, "penalties_b": self.stats.penalties_b
            },
            # Backward-compat dla istniejących wypisów
            "score_a": score_a,
            "score_b": score_b,
            "goals_a": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_a],
            "goals_b": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_b],
            # Per-player effort/energy
            "player_stats": {
                self.team_a.name: build_player_stats(self.team_a),
                self.team_b.name: build_player_stats(self.team_b),
            },
        }

    # Utils: logi
    def _add_event(self, minute: int, team: str, event_type: str, description: str) -> None:
        self.events.append({"minute": minute, "team": team, "event_type": event_type, "description": description})
        # śledzenie poprzedniego eventu (anty‑karuzela rzutów rożnych)
        self._prev_event_type = event_type
        self._prev_event_min = minute
        if self.verbose and description:
            print(description)

    def _log_banner(self, text: str) -> None:
        self.events.append({"minute": 0, "team": "", "event_type": "banner", "description": text})
        if self.verbose:
            print("\n" + "=" * 80)
            print(text)
            print("=" * 80 + "\n")

    def _log_line(self, text: str) -> None:
        self.events.append({"minute": 0, "team": "", "event_type": "info", "description": text})
        if self.verbose and text:
            print(text)

    # Heurystyki
    def _style_control_factor(self, style: str) -> float:
        style = (style or "").lower()
        if style == "attacking": return 1.03
        if style == "defensive": return 0.98
        return 1.0

    def _mental_attr(self, p: Player, key: str, default: float = 50.0) -> float:
        try:
            attrs = getattr(p, 'attributes', {}) or {}
            ment = attrs.get('mental', {}) or {}
            v = float(ment.get(key, default))
            return v
        except Exception:
            return default

    def _avg_aggression(self, team: Team) -> float:
        pool = self._active_players(team)
        pref = [pp for pp in pool if (getattr(pp, 'position', '').upper() in ('DEF','MID'))]
        base = pref if pref else (pool or [])
        if not base:
            return 50.0
        vals = [self._mental_attr(pp, 'aggression', 50.0) for pp in base]
        return sum(vals) / len(vals)

    def _control_modifier(self, team: Team) -> float:
        p_lvl = 0
        try:
            p_lvl = team.pressing_level()
        except Exception:
            pass
        if p_lvl > 0:
            press_factor = 0.98
        elif p_lvl < 0:
            press_factor = 1.02
        else:
            press_factor = 1.0
        w_lvl = 0
        try:
            w_lvl = team.width_level()
        except Exception:
            pass
        if w_lvl > 0:
            width_factor = 0.99
        elif w_lvl < 0:
            width_factor = 1.01
        else:
            width_factor = 1.0
        return press_factor * width_factor

    def _team_attack_value(self, team: Team, minute: int) -> float:
        base = self.strength_a["attack"] if team is self.team_a else self.strength_b["attack"]
        style = (team.style or "").lower()
        if style == "attacking": base *= 1.05
        elif style == "defensive": base *= 0.97
        if self._team_has_active_buff(team, minute): base *= 1.0 + BUFF_PERCENT
        return base

    def _team_defense_value(self, team: Team, minute: int) -> float:
        base = self.strength_a["defense"] if team is self.team_a else self.strength_b["defense"]
        style = (team.style or "").lower()
        if style == "defensive": base *= 1.07
        elif style == "attacking": base *= 0.98
        if self._team_has_active_buff(team, minute): base *= 1.0 + BUFF_PERCENT * 0.5
        return base

    def _keeper_overall(self, team: Team) -> float:
        pool = self._active_players(team)
        gks = [p for p in pool if (p.position or "").upper() == "GK"]
        if not gks: return 70.0
        return max(self._player_overall(p) for p in gks)

    def _player_overall(self, p: Player) -> float:
        def mean(d: Dict[str, float]) -> float:
            if not d: return 70.0
            return sum(d.values()) / max(1, len(d))
        attrs = getattr(p, "attributes", {})
        base = 0.5 * mean(attrs.get("physical", {})) + 0.35 * mean(attrs.get("technical", {})) + 0.15 * mean(attrs.get("mental", {}))
        form = getattr(p, "form", 1.0) or 1.0
        energy = getattr(p, "energy", 1.0) or 1.0
        return base * form * energy

    def _pick_attacker(self, team: Team) -> Player:
        pool_all = self._active_players(team)
        forwards = [p for p in pool_all if (p.position or "").upper() == "FWD"]
        mids = [p for p in pool_all if (p.position or "").upper() == "MID"]
        defs = [p for p in pool_all if (p.position or "").upper() == "DEF"]
        pool = forwards or mids or defs or pool_all
        return random.choice(pool)

    def _pick_defender(self, team: Team) -> Player:
        pool_all = self._active_players(team)
        defs = [p for p in pool_all if (p.position or "").upper() == "DEF"]
        mids = [p for p in pool_all if (p.position or "").upper() == "MID"]
        gks = [p for p in pool_all if (p.position or "").upper() == "GK"]
        pool = defs or mids or gks or pool_all
        return random.choice(pool)

    def _maybe_assist(self, team: Team, prefer: Optional[Player] = None) -> Optional[str]:
        if random.random() < 0.6:
            pool = self._active_players(team)
            candidates = [p for p in pool if (prefer is None or p.name != prefer.name)]
            if candidates: return random.choice(candidates).name
        return None

    def _prob_shot(self, team: Team, defending_team: Optional[Team] = None) -> float:
        base = BASE_SHOT_PROB
        style = (team.style or "").lower()
        if style == "attacking": base += STYLE_ATK_SHOT_BONUS
        elif style == "defensive": base -= STYLE_DEF_SHOT_MALUS
        ch = (team.attack_channel or "").lower()
        if ch == "wings": base += WINGS_SHOT_BONUS
        # Width synergy
        try:
            w = team.width_level()
        except Exception:
            w = 0
        if w > 0:
            if ch == "wings": base += 0.012
            elif ch == "center": base -= 0.008
        elif w < 0:
            if ch == "center": base += 0.012
            elif ch == "wings": base -= 0.008
        # Pressing effects
        try:
            p_att = team.pressing_level()
        except Exception:
            p_att = 0
        if p_att > 0: base *= 1.04
        elif p_att < 0: base *= 0.96
        if defending_team is not None:
            try:
                p_def = defending_team.pressing_level()
            except Exception:
                p_def = 0
            if p_def > 0: base *= 0.97
            elif p_def < 0: base *= 1.02
        return max(0.05, min(0.60, base))

    def _prob_shot_on_target(self, atk: float, defv: float) -> float:
        ratio = atk / max(1.0, defv)
        base = 0.25 * min(1.5, ratio)
        return max(0.12, min(0.55, base))

    def _prob_goal(self, shot_power: float, keeper_ovr: float) -> float:
        ratio = shot_power / max(1.0, keeper_ovr)
        base = 0.18 * min(1.6, ratio)
        return max(0.04, min(0.35, base))

    def _pick_duel_minutes(self, half: int, count: int) -> List[int]:
        segments = [(5, 15), (16, 30), (31, 45)] if half == 1 else [(50, 60), (61, 75), (76, 90)]
        return sorted(random.randint(a, b) for (a, b) in segments[:min(count, len(segments))])

    # Przerwa
    def _half_time_adjustments(self) -> None:
        for team in (self.team_a, self.team_b):
            sorted_by_energy = sorted(team.players, key=lambda p: getattr(p, "energy", 1.0))
            for p in sorted_by_energy[:2]:
                p.energy = min(1.0, (getattr(p, "energy", 1.0) or 1.0) + RESTORE_ENERGY)
                self._add_event(0, team.name, "half_rest", f"🔋 PRZERWA: {p.name} +20% energii.")
            key_player = max(team.players, key=lambda x: self._player_overall(x))
            buff_end = HALF_SIM_MINUTES + BUFF_DURATION_MIN
            self.buff_until[key_player.name] = buff_end
            self._add_event(0, team.name, "half_buff", f"🚀 PRZERWA: {key_player.name} buff +10% na {BUFF_DURATION_MIN} min.")
        # Zmiany taktyczne na przerwie zależnie od wyniku
        self._maybe_tactical_adjustments_at_halftime()
        # Po ewentualnych zmianach stylu przelicz siły
        self._recompute_strengths()

    # Aktywni zawodnicy (pierwsza XI) pomocniczo
    def _active_players(self, team: Team) -> List[Player]:
        idx = self._active_idx.get(team.name) or set()
        if not idx:
            # fallback, pierwszych 11 lub wszyscy
            return team.players[:min(11, len(team.players))] if team.players else []
        ordered = [i for i in sorted(idx) if 0 <= i < len(team.players)]
        return [team.players[i] for i in ordered]

    def _attempt_substitutions(self, minute: int) -> None:
        # Obie drużyny próbują zrobić 1 zmianę, jeżeli mają ławkę
        for team in (self.team_a, self.team_b):
            self._attempt_substitution(team, minute)

    def _attempt_substitution(self, team: Team, minute: int) -> None:
        name = team.name
        if self._subs_left.get(name, 0) <= 0:
            return
        total = len(team.players)
        active = self._active_idx.get(name, set())
        if total <= len(active):
            return  # brak ławki
        # wybierz najbardziej zmęczonego zawodnika z pola (nie GK)
        active_list = [(i, team.players[i]) for i in active]
        out_candidates = [(i, p) for (i, p) in active_list if (getattr(p, 'position', '').upper() != 'GK')]
        if not out_candidates:
            return
        out_i, out_p = min(out_candidates, key=lambda ip: getattr(ip[1], 'energy', 1.0))
        # wybierz rezerwowego (preferuj tę samą pozycję)
        bench_idx = [i for i in range(total) if i not in active]
        same_pos = [i for i in bench_idx if (getattr(team.players[i], 'position', '').upper() == getattr(out_p, 'position', '').upper())]
        in_i = (same_pos[0] if same_pos else bench_idx[0]) if bench_idx else None
        if in_i is None:
            return
        in_p = team.players[in_i]
        # wykonaj zmianę
        active.remove(out_i)
        active.add(in_i)
        self._active_idx[name] = active
        self._subs_left[name] = max(0, self._subs_left.get(name, 0) - 1)
        self.substitutions.append({
            'minute': minute,
            'team': name,
            'out': out_p.name,
            'in': in_p.name,
            'reason': 'zmęczenie'
        })
        self._add_event(minute, name, 'substitution', f"{minute}' - 🔁 Zmiana w {name}: {out_p.name} ▶ {in_p.name}")
        # Po zmianie przelicz siły
        self._recompute_strengths()

    def _style_mod(self, style: str) -> Tuple[float, float]:
        s = (style or 'balanced').lower()
        if s == 'attacking':
            return 1.10, 0.95
        if s == 'defensive':
            return 0.95, 1.10
        return 1.0, 1.0

    def _team_strength_from_active(self, team: Team, active: List[Player]) -> Dict[str, float]:
        if not active:
            return {'attack': 50.0, 'defense': 50.0, 'control': 50.0, 'overall': 50.0}
        atk_pool = [p for p in active if (getattr(p, 'position', '').upper() in ('FWD', 'MID'))]
        def_pool = [p for p in active if (getattr(p, 'position', '').upper() in ('DEF', 'GK'))]
        atk_pool = sorted(atk_pool, key=lambda p: self._player_overall(p), reverse=True)[:5] or active[:5]
        def_pool = sorted(def_pool, key=lambda p: self._player_overall(p), reverse=True)[:5] or active[:5]
        base_attack = sum(self._player_overall(p) for p in atk_pool) / max(1, len(atk_pool))
        base_defense = sum(self._player_overall(p) for p in def_pool) / max(1, len(def_pool))
        control = sum(self._player_overall(p) for p in active) / max(1, len(active))
        modA, modD = self._style_mod(getattr(team, 'style', 'balanced'))
        return {
            'attack': base_attack * modA,
            'defense': base_defense * modD,
            'control': control,
            'overall': (base_attack * modA + base_defense * modD + control) / 3.0,
        }

    def _recompute_strengths(self) -> None:
        a_active = self._active_players(self.team_a)
        b_active = self._active_players(self.team_b)
        self.strength_a = self._team_strength_from_active(self.team_a, a_active)
        self.strength_b = self._team_strength_from_active(self.team_b, b_active)

    def _maybe_tactical_adjustments_at_halftime(self) -> None:
        score_a = len(self.stats.goals_a)
        score_b = len(self.stats.goals_b)
        # trailing -> ofensywnie, leading -> defensywnie
        if score_a < score_b:
            self.team_a.style = 'attacking'; self.team_a.pressing = 'high'
            self._add_event(HALF_SIM_MINUTES, self.team_a.name, 'tactical_change', f"45' - ⚙️ Zmiana taktyki {self.team_a.name}: styl=attacking, pressing=high")
        elif score_a > score_b:
            self.team_b.style = 'attacking'; self.team_b.pressing = 'high'
            self._add_event(HALF_SIM_MINUTES, self.team_b.name, 'tactical_change', f"45' - ⚙️ Zmiana taktyki {self.team_b.name}: styl=attacking, pressing=high")
        # lekka korekta szerokości dla zespołu prowadzącego (zamykanie środka)
        if score_a > score_b:
            self.team_a.width = 'narrow'
        elif score_b > score_a:
            self.team_b.width = 'narrow'

    def _maybe_tactical_change_in_play(self, minute: int) -> None:
        score_a = len(self.stats.goals_a)
        score_b = len(self.stats.goals_b)
        # Około 70' – korekty w zależności od wyniku
        if score_a < score_b:
            self.team_a.style = 'attacking'; self.team_a.pressing = 'high'; self.team_a.width = 'wide'
            self._add_event(minute, self.team_a.name, 'tactical_change', f"{minute}' - ⚙️ {self.team_a.name} podkręca: styl=attacking, pressing=high, width=wide")
        elif score_b < score_a:
            self.team_b.style = 'attacking'; self.team_b.pressing = 'high'; self.team_b.width = 'wide'
            self._add_event(minute, self.team_b.name, 'tactical_change', f"{minute}' - ⚙️ {self.team_b.name} podkręca: styl=attacking, pressing=high, width=wide")
        # po zmianach stylu przelicz siły
        self._recompute_strengths()

    def _team_has_active_buff(self, team: Team, minute: int) -> bool:
        if minute <= HALF_SIM_MINUTES: return False
        for p in team.players:
            end = self.buff_until.get(p.name)
            if end and minute <= end: return True
        return False

    # Doliczony czas
    def _compute_stoppage_time(self) -> int:
        base = self._h2_stoppages
        jitter = random.uniform(-0.3, 0.4)
        est = max(0.0, base + jitter)
        if est < 1.0: return 1
        if est < 2.0: return 2
        if est < 3.0: return 3
        if est < 4.0: return 4
        if est < 5.0: return 5
        return 6

    # ─────────────────────────────  ZMĘCZENIE / DYSTANS  ─────────────────────────
    def _apply_minute_fatigue(self, minute: int, in_pos: Team, defe: Team, att_p: Optional[Player], def_p: Optional[Player]) -> None:
        if self._fatigue_last_minute == minute:
            return
        self._fatigue_last_minute = minute

        base_drain = 0.0028

        def pos_mult(p: Player) -> float:
            pos = (getattr(p, 'position', '') or '').upper()
            if pos == 'GK': return 0.5
            if pos == 'DEF': return 0.9
            if pos == 'MID': return 1.1
            if pos == 'FWD': return 1.0
            return 1.0

        def style_mult(team: Team) -> float:
            s = (getattr(team, 'style', 'balanced') or '').lower()
            if s == 'attacking': return 1.05
            if s == 'defensive': return 0.97
            return 1.0

        def press_mult(team: Team) -> float:
            try:
                pl = team.pressing_level()
            except Exception:
                pl = 0
            if pl > 0: return 1.10
            if pl < 0: return 0.92
            return 1.0

        def width_mult(team: Team) -> float:
            try:
                wl = team.width_level()
            except Exception:
                wl = 0
            if wl > 0: return 1.05
            if wl < 0: return 0.98
            return 1.0

        def channel_mult(team: Team, is_possession: bool) -> float:
            if not is_possession:
                return 1.0
            ch = (getattr(team, 'attack_channel', 'center') or '').lower()
            if ch == 'wings': return 1.03
            return 1.0

        def stamina_mult(p: Player) -> float:
            try:
                attrs = getattr(p, 'attributes', {}) or {}
                stam = float((attrs.get('physical', {}) or {}).get('stamina', 75))
            except Exception:
                stam = 75.0
            return max(0.9, min(1.1, 1.0 - (stam - 60.0)/400.0))

        def apply_for_team(team: Team, is_possession: bool) -> None:
            m_team = style_mult(team) * press_mult(team) * width_mult(team) * channel_mult(team, is_possession)
            for p in self._active_players(team):
                m_p = pos_mult(p) * stamina_mult(p)
                drain = base_drain * m_team * m_p
                key = (team.name, getattr(p, 'id', p.name))
                # dodatkowy koszt gdy uczestnik pojedynku w tej minucie
                if att_p is not None and p is att_p:
                    drain += 0.002
                if def_p is not None and p is def_p:
                    drain += 0.002
                # aktualizacja energii
                try:
                    new_e = max(0.60, min(1.0, (getattr(p, 'energy', 1.0) or 1.0) - drain))
                    p.energy = new_e
                except Exception:
                    pass
                # akumulacja „load” do dystansu
                self._p_load[key] = self._p_load.get(key, 0.0) + (drain / base_drain)

        apply_for_team(in_pos, True)
        apply_for_team(defe, False)
