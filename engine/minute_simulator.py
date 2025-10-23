from __future__ import annotations
"""
engine/minute_simulator.py

TODO: Odpowiada za logikę zdarzeń w pojedynczej minucie meczu.
API: simulate_minute(engine, half, minute)
Bez zmian funkcjonalnych — deleguje do metod engine (_simulate_*_internal).
"""
from typing import Any


def simulate_minute(engine: Any, half: int, minute: int) -> None:
    # uproszczona logika jak w pętli simulate_match
    rng = engine._rng
    attacker = engine.team_a if (rng.random() < 0.5) else engine.team_b
    defender = engine.team_b if attacker is engine.team_a else engine.team_a
    roll = rng.random()
    # zlicz posiadanie
    if attacker is engine.team_a:
        engine.possession_a_ticks += 1
    else:
        engine.possession_b_ticks += 1
    if roll < 0.06:
        engine._simulate_foul_internal(minute, attacker, defender)
    elif roll < 0.18:
        engine._simulate_duel_internal_new(minute, attacker, defender)
    elif roll < 0.26:
        engine._simulate_set_piece_internal(minute, attacker, defender)
    elif roll < 0.52:
        shooter = rng.choice(attacker.players).name if attacker.players else "Zawodnik"
        on_target = rng.random() < 0.60
        if attacker is engine.team_a:
            engine.stats.shots_a += 1
            if on_target:
                engine.stats.shots_on_a += 1
        else:
            engine.stats.shots_b += 1
            if on_target:
                engine.stats.shots_on_b += 1
        # xG heurystyka (prosty model): baza + modyfikatory i clamp
        base = 0.08
        if on_target:
            base += 0.06
        last_win = engine._last_duel_win_minute.get(attacker.name, 0)
        if last_win and (minute - last_win) <= 10:
            base += 0.08
        if (minute % 5) == 0:
            base += 0.10
        shot_xg = max(0.02, min(0.40, base))
        if attacker is engine.team_a:
            engine.stats.xg_a += shot_xg
        else:
            engine.stats.xg_b += shot_xg
        goal = on_target and (rng.random() < 0.18)
        if goal:
            if attacker is engine.team_a:
                engine.stats.goals_a.append((minute, shooter, None))
            else:
                engine.stats.goals_b.append((minute, shooter, None))
            engine._emit_commentary(minute, 'goal', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='goal')
        else:
            if on_target:
                engine._emit_commentary(minute, 'shot_saved', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='shot_on_target')
            else:
                engine._emit_commentary(minute, 'shot_off', {'name': shooter, 'att': shooter, 'def': '', 'team': attacker.name, 'minute': minute}, final_kind='shot_off_target')
    # fatigue/injury tick
    try:
        from engine.fatigue import apply_fatigue_tick, FatigueContext
        from engine.injury import maybe_injury
        ctx = FatigueContext(minute=minute, team_in_possession=attacker, defending_team=defender)
        active_a = attacker.players[:min(11, len(attacker.players))]
        active_b = defender.players[:min(11, len(defender.players))]
        apply_fatigue_tick(active_a, active_b, ctx)
        # kontuzje: tylko redukcja slotów, bez eventów
        if active_a:
            v1 = rng.choice(active_a)
            evt1 = maybe_injury(v1, minute, attacker, strict_ref=False, opponent_high_press=False)
            if evt1 and evt1.requires_sub and engine._subs_left.get(attacker.name, 0) > 0:
                engine._subs_left[attacker.name] -= 1
        if active_b:
            v2 = rng.choice(active_b)
            evt2 = maybe_injury(v2, minute, defender, strict_ref=False, opponent_high_press=False)
            if evt2 and evt2.requires_sub and engine._subs_left.get(defender.name, 0) > 0:
                engine._subs_left[defender.name] -= 1
    except Exception:
        pass
