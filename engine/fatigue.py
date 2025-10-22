from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from models.player import Player
from models.team import Team
from .config import get_config


@dataclass
class FatigueContext:
    minute: int
    team_in_possession: Team
    defending_team: Team
    duel_pair: Tuple[Optional[Player], Optional[Player]] = (None, None)
    sprint_success: bool = False


def _drain_for_player(p: Player, *, base_norm: float, team_mult: float, duel_bonus: float, sprint_bonus: float) -> float:
    pos = (getattr(p, 'position', '') or '').upper()
    if pos == 'GK':
        pos_mult = 0.5
    elif pos == 'DEF':
        pos_mult = 0.9
    elif pos == 'MID':
        pos_mult = 1.1
    else:  # FWD or other
        pos_mult = 1.0

    # Work rate multiplier (defaults to 'med')
    wr = getattr(p, 'work_rate', 'med') or 'med'
    wr_mult = get_config().get(f'fatigue.work_rate_mult.{wr}', 1.0)

    # stamina_base provides minor reduction for very good stamina
    try:
        s_base = float(getattr(p, 'stamina_base', 75) or 75)
    except Exception:
        s_base = 75.0
    stamina_mult = max(0.9, min(1.1, 1.0 - (s_base - 60.0) / 400.0))

    drain = base_norm * team_mult * pos_mult * wr_mult * stamina_mult
    drain += duel_bonus + sprint_bonus
    return drain


def apply_fatigue_tick(active_in_pos: Iterable[Player], active_def: Iterable[Player], ctx: FatigueContext) -> None:
    cfg = get_config()
    # Base drain per minute in [0..100] scaled to normalized [0..1]
    base_100 = float(cfg.get('fatigue.base_drain_per_min_100', 0.25))
    base_norm = base_100 / 100.0

    # Team modifiers
    def pressing_high(team: Team) -> bool:
        try:
            return (team.pressing or 'normal').lower() == 'high'
        except Exception:
            return False

    team_mult_in = 1.0
    team_mult_def = 1.0
    if pressing_high(ctx.team_in_possession):
        team_mult_in += float(cfg.get('fatigue.pressing_high_extra', 0.15))
    if pressing_high(ctx.defending_team):
        team_mult_def += float(cfg.get('fatigue.pressing_high_extra', 0.15))

    # Duel and sprint context bonuses (normalized)
    att_p, def_p = ctx.duel_pair
    duel_bonus = (float(cfg.get('fatigue.duel_participation_extra', 0.2)) / 100.0)
    sprint_bonus = (float(cfg.get('fatigue.sprint_success_extra', 0.25)) / 100.0) if ctx.sprint_success else 0.0

    # Distance model params
    base_speed = float(cfg.get('fatigue.distance.base_speed_km_per_min', 0.115))
    style_mults = cfg.get('fatigue.distance.style_mult', {'attacking':1.03,'balanced':1.0,'defensive':0.98})
    press_mults = cfg.get('fatigue.distance.pressing_mult', {'high':1.05,'normal':1.0,'low':0.97})
    pos_mults = cfg.get('fatigue.distance.position_mult', {'GK':0.50,'DEF':0.95,'MID':1.06,'FWD':1.00})
    wr_mults = cfg.get('fatigue.distance.work_rate_mult', {'low':0.95,'med':1.0,'high':1.07})
    sprint_boost_km = float(cfg.get('fatigue.distance.sprint_boost_km', 0.03))

    def style_m(team: Team, is_pos: bool) -> float:
        try:
            s = (team.style or 'balanced').lower()
        except Exception:
            s = 'balanced'
        return float(style_mults.get(s, 1.0))

    def press_m(team: Team) -> float:
        try:
            p = (team.pressing or 'normal').lower()
        except Exception:
            p = 'normal'
        return float(press_mults.get(p, 1.0))

    # Update energy and distance for players
    def update(players: Iterable[Player], team_mult: float, *, team: Team, is_pos: bool) -> None:
        for p in players:
            extra = 0.0
            if att_p is not None and p is att_p:
                extra += duel_bonus
            if def_p is not None and p is def_p:
                extra += duel_bonus
            drain = _drain_for_player(p, base_norm=base_norm, team_mult=team_mult, duel_bonus=extra, sprint_bonus=sprint_bonus if (p is att_p) else 0.0)
            try:
                cur = float(getattr(p, 'energy', 1.0) or 1.0)
                new_e = max(0.0, min(1.0, cur - drain))
                p.energy = new_e
            except Exception:
                pass
            # Distance accumulation
            try:
                # stable jitter per player
                if not hasattr(p, '_dist_jitter'):
                    import random as _r
                    setattr(p, '_dist_jitter', _r.uniform(-0.07, 0.07))
                jitter = float(getattr(p, '_dist_jitter', 0.0))
                pos = (getattr(p, 'position', '') or '').upper()
                pos_m = float(pos_mults.get(pos, 1.0))
                wr = (getattr(p, 'work_rate', 'med') or 'med')
                wr_m = float(wr_mults.get(wr, 1.0))
                speed = base_speed * style_m(team, is_pos) * press_m(team) * pos_m * wr_m * (1.0 + jitter)
                # sprint bonus applies only to attacking participant
                bonus = sprint_boost_km if (ctx.sprint_success and p is att_p) else 0.0
                p.distance_km = float(getattr(p, 'distance_km', 0.0) or 0.0) + speed + bonus
            except Exception:
                pass

    update(list(active_in_pos), team_mult_in, team=ctx.team_in_possession, is_pos=True)
    update(list(active_def), team_mult_def, team=ctx.defending_team, is_pos=False)


def effective_skill(player: Player, base_skill: float) -> float:
    cfg = get_config()
    e100 = float(getattr(player, 'energy', 1.0) or 1.0) * 100.0
    mult = 1.0
    # Apply thresholds from lowest energy first
    thresholds = sorted(list(cfg.get('fatigue.thresholds', [])), key=lambda t: float(t.get('energy_lt', 0)))
    for th in thresholds:
        try:
            if e100 < float(th.get('energy_lt', 0)):
                mult = float(th.get('multiplier', 1.0))
                break
        except Exception:
            continue
    return base_skill * mult


def halftime_regen(players: Iterable[Player]) -> None:
    cfg = get_config()
    inc = float(cfg.get('fatigue.halftime_regen_100', 8.0)) / 100.0
    for p in players:
        try:
            p.energy = max(0.0, min(1.0, (getattr(p, 'energy', 1.0) or 1.0) + inc))
        except Exception:
            pass
