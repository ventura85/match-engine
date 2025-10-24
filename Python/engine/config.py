from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import os
import json

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


DEFAULTS: Dict[str, Any] = {
    'fatigue': {
        'base_drain_per_min_100': 0.25,
        'work_rate_mult': {'low': 0.8, 'med': 1.0, 'high': 1.25},
        'pressing_high_extra': 0.15,
        'duel_participation_extra': 0.2,
        'sprint_success_extra': 0.25,
        'distance': {
            'base_speed_km_per_min': 0.115,
            'style_mult': {'attacking': 1.03, 'balanced': 1.0, 'defensive': 0.98},
            'pressing_mult': {'high': 1.05, 'normal': 1.0, 'low': 0.97},
            'position_mult': {'GK': 0.50, 'DEF': 0.95, 'MID': 1.06, 'FWD': 1.00},
            'work_rate_mult': {'low': 0.95, 'med': 1.0, 'high': 1.07},
            'sprint_boost_km': 0.03,
        },
        'thresholds': [
            {'energy_lt': 30, 'multiplier': 0.75},
            {'energy_lt': 50, 'multiplier': 0.88},
            {'energy_lt': 70, 'multiplier': 0.95},
        ],
        'halftime_regen_100': 8.0,
    },
    'injuries': {
        'p_base_per_min': 0.0008,
        'energy_mult': {'lt40': 1.5, 'lt25': 2.0},
        'context_mult': {'strict_referee_and_high_press': 1.2},
        'require_sub_probability': {'minor': 0.10, 'moderate': 0.50, 'severe': 0.90},
    },
    'sfg': {
        'corner_schemes': {
            'short':       {'shot_prob': 0.18, 'shot_on_target': 0.42, 'foul_attack': 0.06, 'fast_counter': 0.10},
            'near_post':   {'shot_prob': 0.34, 'shot_on_target': 0.38, 'foul_attack': 0.08, 'fast_counter': 0.12},
            'far_post':    {'shot_prob': 0.32, 'shot_on_target': 0.40, 'foul_attack': 0.06, 'fast_counter': 0.10},
            'crowd_keeper':{'shot_prob': 0.28, 'shot_on_target': 0.44, 'foul_attack': 0.10, 'fast_counter': 0.14},
        },
        'freekick': {
            'direct_goal_xg': 0.06,
            'indirect_cross_shot_on': 0.32,
            'indirect_xg': 0.07,
        },
    },
    'xg_weights': {
        'freekick_indirect': 0.06,
        'open_play_shot': 0.09,
        'penalty': 0.76,
        'corner': 0.05,
    },
    'rules': {
        'duels_per_half': 3,
        'halftime_buff_percent': 10,
        'halftime_buff_duration_min': 20,
    },
    'distributions': {
        'goals_per_match_range': [2.2, 4.2],
        'sfg_goal_share_range': [0.15, 0.35],
        'yellows_per_match_range': [2.0, 5.5],
    },
    'zones': {'enable_zones': True, 'third_entry_prob': 0.18, 'box_entry_prob': 0.09},
    'telemetry': {'deviation_warn_threshold': 0.15, 'baseline_file': 'out/baseline_distribution.json'},
}


@dataclass
class EngineConfig:
    data: Dict[str, Any] = field(default_factory=lambda: json.loads(json.dumps(DEFAULTS)))

    def get(self, path: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in path.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur


_GLOBAL_CONFIG: Optional[EngineConfig] = None


def load_config(path: str = 'engine_config.yml') -> EngineConfig:
    global _GLOBAL_CONFIG
    cfg = EngineConfig()
    if os.path.exists(path) and yaml is not None:
        with open(path, 'r', encoding='utf-8') as f:
            loaded = yaml.safe_load(f) or {}
        # deep-merge into defaults
        def merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(a)
            for k, v in (b or {}).items():
                if isinstance(v, dict) and isinstance(out.get(k), dict):
                    out[k] = merge(out[k], v)
                else:
                    out[k] = v
            return out
        cfg.data = merge(DEFAULTS, loaded)
    _GLOBAL_CONFIG = cfg
    return cfg


def get_config() -> EngineConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = load_config()
    return _GLOBAL_CONFIG
