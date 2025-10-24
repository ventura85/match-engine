from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import random

from models.player import Player
from models.team import Team
from .config import get_config


@dataclass
class InjuryEvent:
    type: str  # 'minor' | 'moderate' | 'severe'
    requires_sub: bool
    time_minute: int
    player_id: int
    player_name: str
    team_name: str
    est_recovery_days: Optional[int] = None


def _base_prob(context: Dict[str, Any]) -> float:
    cfg = get_config()
    p = float(cfg.get('injuries.p_base_per_min', 0.0008))
    # energy effects
    energy = float(context.get('energy_100', 100.0))
    if energy < 25:
        p *= float(cfg.get('injuries.energy_mult.lt25', 2.0))
    elif energy < 40:
        p *= float(cfg.get('injuries.energy_mult.lt40', 1.5))
    # strict ref + high press context
    if context.get('strict_ref') and context.get('opp_high_press'):
        p *= float(cfg.get('injuries.context_mult.strict_referee_and_high_press', 1.2))
    return p


def maybe_injury(player: Player, minute: int, team: Team, *, strict_ref: bool, opponent_high_press: bool) -> Optional[InjuryEvent]:
    rng = random
    ctx = {
        'energy_100': float(getattr(player, 'energy', 1.0) or 1.0) * 100.0,
        'strict_ref': bool(strict_ref),
        'opp_high_press': bool(opponent_high_press),
    }
    p = _base_prob(ctx)
    if rng.random() >= p:
        return None

    # choose severity
    r = rng.random()
    if r < 0.70:
        sev = 'minor'
    elif r < 0.93:
        sev = 'moderate'
    else:
        sev = 'severe'

    rp = get_config().get('injuries.require_sub_probability', {'minor': 0.10, 'moderate': 0.50, 'severe': 0.90})
    requires_sub = (rng.random() < float(rp.get(sev, 0.5)))
    return InjuryEvent(
        type=sev,
        requires_sub=requires_sub,
        time_minute=minute,
        player_id=getattr(player, 'id', 0),
        player_name=getattr(player, 'name', ''),
        team_name=getattr(team, 'name', ''),
        est_recovery_days=None,
    )

