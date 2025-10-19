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

# Tempo
DEFAULT_REAL_MINUTES = 2
TOTAL_SIM_MINUTES = 90
HALF_SIM_MINUTES = 45

# Parametry zdarzeń
BASE_SHOT_PROB = 0.20
STYLE_ATK_SHOT_BONUS = 0.08
STYLE_DEF_SHOT_MALUS = 0.05
WINGS_SHOT_BONUS = 0.02

SAVE_TO_CORNER_PROB = 0.45
BLOCK_TO_CORNER_PROB = 0.30

FOUL_PROB_PER_MIN = 0.08
STYLE_DEF_FOUL_BONUS = 0.02
YELLOW_PROB = 0.28
SECOND_YELLOW_TO_RED_PROB = 0.25
DIRECT_RED_PROB = 0.04

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
        density: str = "high"  # domyślnie high dla MMO, ale bez „ultra”
    ) -> None:
        self.team_a = team_a
        self.team_b = team_b
        self.verbose = verbose

        self.real_time = bool(real_time)
        self.real_minutes_target = max(1, int(real_minutes_target))
        self.seconds_per_sim_minute = (self.real_minutes_target * 60.0) / TOTAL_SIM_MINUTES

        self.strength_a = calculate_team_strength(self.team_a)
        self.strength_b = calculate_team_strength(self.team_b)

        self.events: List[Dict] = []
        self.stats = MatchStats()
        self.duel = DuelSystem()

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
        self._add_event(90 + added, "", "final_whistle", C.final_whistle())
        if self.verbose:
            print(C.final_whistle())
        return self._generate_report()

    # minuta meczu
    def _simulate_minute(self, half: int, minute: int) -> None:
        ctrl_a = self.strength_a["control"] * self._style_control_factor(self.team_a.style)
        ctrl_b = self.strength_b["control"] * self._style_control_factor(self.team_b.style)
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
            return

        if self._minute_foul_occurs(team_in_possession):
            self._simulate_foul(half, minute, team_in_possession)
            self._maybe_micro(minute, team_in_possession, defending_team)
            return

        self._simulate_action(half, minute, team_in_possession)
        self._maybe_micro(minute, team_in_possession, defending_team)

    def _simulate_action(self, half: int, minute: int, attacking_team: Team) -> None:
        defending_team = self.team_b if attacking_team is self.team_a else self.team_a
        atk = self._team_attack_value(attacking_team, minute)
        defv = self._team_defense_value(defending_team, minute)

        p_shot = self._prob_shot(attacking_team)
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
                    if random.random() < SAVE_TO_CORNER_PROB:
                        self._register_corner(minute, attacking_team, text=C.corner_parried(shooter, attacking_team, defending_team))
                    else:
                        self._add_event(minute, attacking_team.name, "shot_on_target",
                                        f"{minute}' - 🧤 {C.shot_on_target(shooter, attacking_team, defending_team)}")
                else:
                    if random.random() < BLOCK_TO_CORNER_PROB:
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
            if attacking_team is self.team_a:
                self.stats.shots_a += 1; self.stats.shots_on_a += 1
            else:
                self.stats.shots_b += 1; self.stats.shots_on_b += 1

            gk_overall = self._keeper_overall(defending_team)
            att_power = self._team_attack_value(attacking_team, minute) * 1.08
            goal_prob = self._prob_goal(att_power, gk_overall) * 1.12

            if (random.random() < goal_prob) and (minute not in self._minute_goal_lock):
                assist = self._maybe_assist(attacking_team, prefer=att_player)
                self._score_goal(half, minute, attacking_team, att_player.name, assist if assist else None, context=None)
                self._add_event(minute, attacking_team.name, "context",
                                f"{minute}' - {C.duel_context(att_player, def_player)}")
                self._minute_goal_lock.add(minute)
                if minute > HALF_SIM_MINUTES:
                    self._h2_stoppages += 1.0
                return
            else:
                if random.random() < SAVE_TO_CORNER_PROB:
                    self._register_corner(minute, attacking_team, text="Bramkarz z trudem wybija po pojedynku – rzut rożny!")
                else:
                    self._add_event(minute, attacking_team.name, "shot_on_target",
                                    f"{minute}' - 🧤 {C.duel_shot_saved(att_player)}")

        self._add_event(minute, attacking_team.name, f"duel_{result.get('type','action')}",
                        f"{minute}' - ⚔️ {result.get('detail','Zacięta walka o piłkę...')}")

    # MICRO-EVENTY (tanie: nie zmieniają statystyk)
    def _maybe_micro(self, minute: int, att: Team, defe: Team) -> None:
        cfg = self._dconf
        if random.random() > cfg["micro_prob"]:
            return
        count = random.randint(cfg["micro_min"], cfg["micro_max"])
        if count <= 0:
            return
        for _ in range(count):
            r = random.random()
            if r < 0.35:
                txt = C.micro_pass_chain(att, defe)
            elif r < 0.55:
                txt = C.micro_press(att, defe)
            elif r < 0.70:
                txt = C.micro_throw_in(att)
            elif r < 0.85:
                txt = C.micro_goal_kick(defe)
            else:
                txt = C.micro_clearance(att, defe)
            self._add_event(minute, att.name, "micro", f"{minute}' - {txt}")

    # Faule / SFG / kartki
    def _minute_foul_occurs(self, attacking_team: Team) -> bool:
        defending = self.team_b if attacking_team is self.team_a else self.team_a
        p = FOUL_PROB_PER_MIN + (STYLE_DEF_FOUL_BONUS if (defending.style or '').lower() == 'defensive' else 0.0)
        return random.random() < max(0.0, min(0.30, p))

    def _simulate_foul(self, half: int, minute: int, attacking_team: Team) -> None:
        defending_team = self.team_b if attacking_team is self.team_a else self.team_a

        if attacking_team is self.team_a: self.stats.fouls_b += 1
        else: self.stats.fouls_a += 1

        if minute > HALF_SIM_MINUTES:
            self._h2_stoppages += 0.5

        foul_place_box = (random.random() < 0.22)
        booked_player = self._pick_defender(defending_team).name
        card_txt = ""

        # kartki
        if random.random() < DIRECT_RED_PROB:
            self._give_red(defending_team, booked_player)
            card_txt = f" {C.red_card(booked_player)}"
            if minute > HALF_SIM_MINUTES:
                self._h2_stoppages += 0.7
        else:
            if random.random() < YELLOW_PROB:
                is_second = self._give_yellow(defending_team, booked_player)
                if is_second and (random.random() < SECOND_YELLOW_TO_RED_PROB):
                    self._give_red(defending_team, booked_player)
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

    def _give_red(self, team: Team, player_name: str) -> None:
        if team is self.team_a: self.stats.reds_a += 1
        else: self.stats.reds_b += 1
        self._add_event(0, team.name, "red_card", f"{C.red_card(player_name)}")

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
            self._add_event(minute, team.name, "goal_penalty", desc)
        elif context == "freekick":
            desc = f"{minute}' - ⚽ GOL! {team.name}! Strzelec: {scorer}{assist_txt} — {C.freekick_goal(scorer, team)}{extra_txt}"
            self._add_event(minute, team.name, "goal_freekick", desc)
        else:
            self._add_event(minute, team.name, "goal", f"{minute}' - ⚽ GOL! {team.name}! Strzelec: {scorer}{assist_txt}")

    def _generate_report(self) -> Dict:
        total_ticks = max(1, self.stats.pos_a_ticks + self.stats.pos_b_ticks)
        pos_a = round(100.0 * self.stats.pos_a_ticks / total_ticks, 1)
        pos_b = round(100.0 * self.stats.pos_b_ticks / total_ticks, 1)
        return {
            "team_a": self.team_a.name,
            "team_b": self.team_b.name,
            "score_a": len(self.stats.goals_a),
            "score_b": len(self.stats.goals_b),
            "goals_a": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_a],
            "goals_b": [{"minute": m, "scorer": s, "assist": a} for (m, s, a) in self.stats.goals_b],
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
            "events": self.events
        }

    # Utils: logi
    def _add_event(self, minute: int, team: str, event_type: str, description: str) -> None:
        self.events.append({"minute": minute, "team": team, "event_type": event_type, "description": description})
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
        if style == "attacking": return 1.05
        if style == "defensive": return 0.95
        return 1.0

    def _team_attack_value(self, team: Team, minute: int) -> float:
        base = self.strength_a["attack"] if team is self.team_a else self.strength_b["attack"]
        style = (team.style or "").lower()
        if style == "attacking": base *= 1.1
        elif style == "defensive": base *= 0.9
        if self._team_has_active_buff(team, minute): base *= 1.0 + BUFF_PERCENT
        return base

    def _team_defense_value(self, team: Team, minute: int) -> float:
        base = self.strength_a["defense"] if team is self.team_a else self.strength_b["defense"]
        style = (team.style or "").lower()
        if style == "defensive": base *= 1.05
        elif style == "attacking": base *= 0.95
        if self._team_has_active_buff(team, minute): base *= 1.0 + BUFF_PERCENT * 0.5
        return base

    def _keeper_overall(self, team: Team) -> float:
        gks = [p for p in team.players if (p.position or "").upper() == "GK"]
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
        forwards = [p for p in team.players if (p.position or "").upper() == "FWD"]
        mids = [p for p in team.players if (p.position or "").upper() == "MID"]
        defs = [p for p in team.players if (p.position or "").upper() == "DEF"]
        pool = forwards or mids or defs or team.players
        return random.choice(pool)

    def _pick_defender(self, team: Team) -> Player:
        defs = [p for p in team.players if (p.position or "").upper() == "DEF"]
        mids = [p for p in team.players if (p.position or "").upper() == "MID"]
        gks = [p for p in team.players if (p.position or "").upper() == "GK"]
        pool = defs or mids or gks or team.players
        return random.choice(pool)

    def _maybe_assist(self, team: Team, prefer: Optional[Player] = None) -> Optional[str]:
        if random.random() < 0.6:
            candidates = [p for p in team.players if (prefer is None or p.name != prefer.name)]
            if candidates: return random.choice(candidates).name
        return None

    def _prob_shot(self, team: Team) -> float:
        base = BASE_SHOT_PROB
        style = (team.style or "").lower()
        if style == "attacking": base += STYLE_ATK_SHOT_BONUS
        elif style == "defensive": base -= STYLE_DEF_SHOT_MALUS
        if (team.attack_channel or "").lower() == "wings": base += WINGS_SHOT_BONUS
        return max(0.05, min(0.50, base))

    def _prob_shot_on_target(self, atk: float, defv: float) -> float:
        ratio = atk / max(1.0, defv)
        base = 0.35 * min(1.5, ratio)
        return max(0.15, min(0.65, base))

    def _prob_goal(self, shot_power: float, keeper_ovr: float) -> float:
        ratio = shot_power / max(1.0, keeper_ovr)
        base = 0.25 * min(1.6, ratio)
        return max(0.05, min(0.50, base))

    def _pick_duel_minutes(self, half: int, count: int) -> List[int]:
        segments = [(5, 15), (16, 30), (31, 45)] if half == 1 else [(50, 60), (61, 75), (76, 90)]
        return sorted(random.randint(a, b) for (a, b) in segments[:count])

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
