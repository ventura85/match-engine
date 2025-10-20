from __future__ import annotations
from typing import Any, Dict, Optional
import math, random, re

ACTIONS_ATTACK = (
    "dribble", "pass", "shoot",
    "penalty_left", "penalty_right", "penalty_center",
)
ACTIONS_DEFENCE = (
    "press", "tackle", "block",
    "gk_close", "gk_stay", "gk_block",
    "gk_dive_left", "gk_dive_right", "gk_stay"
)

def _attr(p: Any, name: str, default: float = 50.0) -> float:
    if isinstance(p, dict):
        return float(p.get(name, default))
    return float(getattr(p, name, default))

def _stamina_mod(x: float) -> float:
    return 0.9 + 0.15 * max(0.0, min(1.0, (x - 40.0) / 60.0))

def _logistic(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _with_rng(rng: random.Random, p: float, swing: float = 0.10) -> float:
    jitter = (rng.random() * 2 - 1) * swing
    return _clamp01(p * (1.0 + jitter))

def _parse_penalty_action(act_att: str) -> Optional[str]:
    s = act_att.strip().lower()
    if s.startswith("penalty"):
        if re.search(r"(left|\bl\b)", s): return "left"
        if re.search(r"(right|\br\b)", s): return "right"
        if re.search(r"(center|centre|\bc\b|mid)", s): return "center"
        return "center"
    return None

def resolve_duel(attacker: Any, defender: Any, act_att: str, act_def: str, rng: Optional[random.Random] = None) -> Dict[str, Any]:
    rng = rng or random.Random()
    act_att = act_att.strip().lower()
    act_def = act_def.strip().lower()

    # --- KARNY ---
    pen_dir = _parse_penalty_action(act_att)
    if pen_dir is not None:
        shooting   = _attr(attacker, "shooting",   65.0)
        decisions  = _attr(attacker, "decisions",  60.0)
        _ = _stamina_mod(_attr(attacker, "stamina", 80.0))
        reflexes   = max(_attr(defender, "reflexes", 60.0), 40.0)
        handling   = max(_attr(defender, "handling", 60.0), 40.0)
        staminaD   = _stamina_mod(_attr(defender, "stamina", 80.0))

        base_goal = _clamp01(0.78 + 0.08 * ((shooting - 60.0) / 40.0))
        gk_power  = (0.6*reflexes + 0.4*handling) * staminaD

        if act_def not in ("gk_dive_left", "gk_dive_right", "gk_stay"):
            act_def = "gk_stay"

        guessed = (
            (pen_dir == "left"   and act_def == "gk_dive_left") or
            (pen_dir == "right"  and act_def == "gk_dive_right") or
            (pen_dir == "center" and act_def == "gk_stay")
        )

        if guessed:
            goal_p = base_goal * (0.55 - (gk_power - 60.0)/400.0)
        else:
            miss_bias = 0.02 + max(0.0, (70.0 - decisions)/350.0)
            goal_p = base_goal * (1.05 - (gk_power - 60.0)/700.0) - miss_bias

        goal_p = _with_rng(rng, _clamp01(goal_p), swing=0.07)
        wide_p = _clamp01(0.05 + (65.0 - (shooting*0.7 + decisions*0.3)) / 300.0)

        if rng.random() < wide_p:
            return {"outcome":"shot_wide","xg":goal_p*0.25,"commentary":[f"❌ Karny zmarnowany – {('lewo' if pen_dir=='left' else 'prawo' if pen_dir=='right' else 'środek')}, ale poza światło bramki."]}

        if rng.random() < goal_p:
            return {"outcome":"goal","xg":goal_p,"scorer":getattr(attacker,"name",getattr(attacker,"id","STRZELAJĄCY")),"commentary":["⚽ Karny wykorzystany! Pewne uderzenie."]}

        # OBRONIONY — poprawiony tekst:
        if guessed:
            how = "wyczuł stronę i broni!"
        else:
            # GK poszedł w złą stronę, ale i tak odbił (np. nogą / końcówkami palców)
            how = "poszedł w złą stronę, ale broni instynktownie!"
        return {"outcome":"shot_saved","xg":goal_p,"commentary":[f"🧤 Karny obroniony – bramkarz {how}"]}

    # --- POZOSTAŁE: dribble / pass / shoot (+ GK 1v1) ---
    if act_att not in ("dribble", "pass", "shoot"):
        raise ValueError(f"Unknown attacker action: {act_att}")
    if act_def not in ACTIONS_DEFENCE:
        raise ValueError(f"Unknown defender action: {act_def}")

    A = {
        "dribbling":   _attr(attacker, "dribbling",   60.0),
        "passing":     _attr(attacker, "passing",     60.0),
        "shooting":    _attr(attacker, "shooting",    60.0),
        "speed":       _attr(attacker, "speed",       60.0),
        "decisions":   _attr(attacker, "decisions",   60.0),
        "positioning": _attr(attacker, "positioning", 60.0),
        "stamina":     _attr(attacker, "stamina",     80.0),
    }
    D = {
        "tackling":     _attr(defender, "tackling",     60.0),
        "marking":      _attr(defender, "marking",      60.0),
        "reflexes":     _attr(defender, "reflexes",     60.0),
        "handling":     _attr(defender, "handling",     60.0),
        "speed":        _attr(defender, "speed",        60.0),
        "positioning":  _attr(defender, "positioning",  60.0),
        "concentration":_attr(defender, "concentration",60.0),
        "stamina":      _attr(defender, "stamina",      80.0),
    }

    att_stam = _stamina_mod(A["stamina"])
    def_stam = _stamina_mod(D["stamina"])

    if act_att == "dribble":
        if act_def == "press":
            att_score = (0.65*A["dribbling"] + 0.35*A["speed"]) * att_stam
            def_score = (0.6*D["marking"] + 0.25*D["speed"] + 0.15*D["concentration"]) * def_stam
        elif act_def == "tackle":
            att_score = (0.7*A["dribbling"] + 0.2*A["speed"] + 0.1*A["decisions"]) * att_stam
            def_score = (0.65*D["tackling"] + 0.2*D["positioning"] + 0.15*D["concentration"]) * def_stam
        else:
            att_score = (0.7*A["dribbling"] + 0.3*A["speed"]) * att_stam
            def_score = (0.5*D["positioning"] + 0.2*D["speed"] + 0.3*D["concentration"]) * def_stam

        z = (att_score - def_score) / 12.0
        p_success = _with_rng(rng, _logistic(z))
        p_foul = 0.12 if act_def == "tackle" else (0.06 if act_def == "press" else 0.02)
        if rng.random() < p_foul * (1.05 - def_stam*0.05):
            return {"outcome":"foul","foul_type":"free_kick","xg":0.0,"commentary":["Faul na dryblującym – rzut wolny."]}

        if rng.random() < p_success:
            return {"outcome":"breakthrough","xg":0.0,"commentary":["✨ Mija rywala i ma otwartą drogę!"]}
        else:
            return {"outcome":"lost","xg":0.0,"commentary":["🚫 Zatrzymany – dobra asekuracja."]}

    if act_att == "pass":
        att_score = (0.7*A["passing"] + 0.2*A["decisions"] + 0.1*A["positioning"]) * att_stam
        if act_def == "press":
            def_score = (0.55*D["marking"] + 0.2*D["speed"] + 0.25*D["concentration"]) * def_stam
        elif act_def == "tackle":
            def_score = (0.5*D["tackling"] + 0.25*D["marking"] + 0.25*D["positioning"]) * def_stam
        else:
            def_score = (0.45*D["positioning"] + 0.3*D["marking"] + 0.25*D["concentration"]) * def_stam

        z = (att_score - def_score) / 11.0
        p_success = _with_rng(rng, _logistic(z))
        p_intercept = _clamp01(0.08 + (def_score - att_score) / 200.0)

        r = rng.random()
        if r < p_intercept:
            return {"outcome":"intercept","xg":0.0,"commentary":["🧲 Przechwyt! Obrona czyta zamiar."]}
        elif r < p_intercept + p_success:
            return {"outcome":"key_pass","xg":0.0,"commentary":["🎯 Kluczowe podanie – otwiera się pozycja strzelecka!"]}
        else:
            return {"outcome":"lost","xg":0.0,"commentary":["❌ Podanie przecięte – okazja przepadła."]}

    if act_att == "shoot":
        shot_quality = (0.7*A["shooting"] + 0.15*A["decisions"] + 0.15*A["positioning"]) * att_stam
        if act_def in ("press","tackle","block"):
            if act_def == "press":
                def_lane = (0.45*D["marking"] + 0.3*D["positioning"] + 0.25*D["concentration"]) * def_stam
            elif act_def == "tackle":
                def_lane = (0.55*D["tackling"] + 0.25*D["positioning"] + 0.2*D["speed"]) * def_stam
            else:
                def_lane = (0.6*D["positioning"] + 0.25*D["marking"] + 0.15*D["speed"]) * def_stam
        else:
            def_lane = (0.25*D["positioning"] + 0.15*D["marking"]) * def_stam

        lane_z = (shot_quality - def_lane) / 12.0
        xg_pre = _with_rng(rng, 0.08 + 0.50 * _logistic(lane_z))

        gk_ref = max(D["reflexes"], 40.0)
        gk_hand = max(D["handling"], 40.0)
        gk_factor = (0.6*gk_ref + 0.4*gk_hand) * def_stam

        on_target = _clamp01(0.35 + (shot_quality - def_lane) / 180.0)
        p_goal_if_on = _clamp01(xg_pre * (0.75 - (gk_factor - 60.0)/300.0))

        if act_def in ("gk_close", "gk_stay", "gk_block"):
            if act_def == "gk_close":
                on_target = _clamp01(on_target - 0.07)
                p_goal_if_on = _clamp01(p_goal_if_on - 0.05)
            elif act_def == "gk_block":
                on_target = _clamp01(on_target - 0.03)
                p_goal_if_on = _clamp01(p_goal_if_on - 0.08)
            else:
                on_target = _clamp01(on_target + 0.02)
                p_goal_if_on = _clamp01(p_goal_if_on - 0.02)

        if rng.random() > on_target:
            return {"outcome":"shot_wide","xg":xg_pre*0.3,"commentary":["❌ Niecelnie – zabrakło precyzji."]}

        if rng.random() < p_goal_if_on:
            return {"outcome":"goal","xg":p_goal_if_on,"scorer":getattr(attacker,"name",getattr(attacker,"id","NAPASTNIK")),"commentary":["⚽ GOOOL! Pewne wykończenie w sytuacji sam na sam."]}

        return {"outcome":"shot_saved","xg":p_goal_if_on,"commentary":["🧤 Bramkarz broni w 1v1! Świetna interwencja."]}

    return {"outcome":"lost","xg":0.0,"commentary":["(brak rozstrzygnięcia)"]}

class DuelSystem:
    ACTIONS_ATTACK = ACTIONS_ATTACK
    ACTIONS_DEFENCE = ACTIONS_DEFENCE

    @staticmethod
    def resolve(attacker: Any, defender: Any, act_att: str, act_def: str, rng: Optional[random.Random]=None) -> Dict[str, Any]:
        return resolve_duel(attacker, defender, act_att, act_def, rng=rng)

__all__ = ["resolve_duel", "DuelSystem", "ACTIONS_ATTACK", "ACTIONS_DEFENCE"]
