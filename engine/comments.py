from __future__ import annotations
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

# Ścieżki do pakietów komentarzy
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "comments"
DEFAULT_PACK = ASSETS_DIR / "pl_fun.json"

def _safe_choice(arr: List[str], fallback: str) -> str:
    if not arr:
        return fallback
    return random.choice(arr)

def _load_pack(path: Path) -> Dict[str, List[str]]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

class Commentary:
    """
    Warstwa komentarzy:
    - Ładuje frazy z JSON (assets/comments/pl_fun.json)
    - Metody zwracają pojedyncze stringi, wybór losowy z puli
    - Każda metoda ma sensowny fallback (gdy brak wpisu w JSON)
    """
    _pack: Dict[str, List[str]] = {}
    _recent: Dict[str, List[str]] = {}
    _no_repeat_window: int = 3

    @classmethod
    def load(cls, pack_path: Optional[Path] = None) -> None:
        path = pack_path or DEFAULT_PACK
        cls._pack = _load_pack(path)
        cls._recent = {}

    # ────────────────────────────── NAGŁÓWKI / META ──────────────────────────────
    @staticmethod
    def stoppage(minutes: int) -> str:
        if minutes <= 0:
            return "➕ Doliczony czas gry: +1'"
        return f"➕ Gramy jeszcze {minutes}'"

    @staticmethod
    def final_whistle() -> str:
        return "🔚 Koniec spotkania!"

    # ───────────────────────────────  SFG / STRZAŁY  ─────────────────────────────
    @classmethod
    def corner_parried(cls, shooter, att, defe) -> str:
        return _safe_choice(cls._pack.get("corner_parried"), "Bramkarz paruje strzał – róg!")

    @classmethod
    def corner_blocked(cls, shooter, att, defe) -> str:
        return _safe_choice(cls._pack.get("corner_blocked"), "Strzał zablokowany – będzie róg!")

    @classmethod
    def shot_on_target(cls, shooter, att, defe) -> str:
        base = cls._pack.get("shot_on_target")
        return _safe_choice(base, f"{getattr(shooter,'name','Zawodnik')} celnie – dobra interwencja bramkarza!")

    @classmethod
    def shot_off_target(cls, shooter, att) -> str:
        base = cls._pack.get("shot_off_target")
        return _safe_choice(base, f"{getattr(shooter,'name','Zawodnik')} niecelnie!")

    @classmethod
    def freekick(cls, team) -> str:
        base = cls._pack.get("freekick")
        return _safe_choice(base, "Rzut wolny – dorzucą w szesnastkę?")

    @classmethod
    def penalty_miss(cls, team) -> str:
        base = cls._pack.get("penalty_miss")
        return _safe_choice(base, "Jedenastka zmarnowana!")

    @classmethod
    def penalty_goal(cls, scorer, team) -> str:
        base = cls._pack.get("penalty_goal")
        return _safe_choice(base, "Jedenastka! Pewnie przy słupku.")

    @classmethod
    def freekick_goal(cls, scorer, team) -> str:
        base = cls._pack.get("freekick_goal")
        return _safe_choice(base, "Nad murem i do siatki – majstersztyk!")

    # ─────────────────────────────  BUDOWANIE AKCJI  ─────────────────────────────
    @classmethod
    def build_up_short(cls, att, defe) -> str:
        return cls._pick_no_repeat("build_up_short", "Krótka klepka, cierpliwe budowanie.")

    @classmethod
    def build_up_medium(cls, att, defe) -> str:
        return cls._pick_no_repeat("build_up_medium", "Zmienna wysokość ataku, wachlowanie piłką – czekają na lukę.")

    # ─────────────────────────────  POJEDYNKI / KONTEKST  ────────────────────────
    @classmethod
    def duel_context(cls, att_player, def_player) -> str:
        base = cls._pack.get("duel_context")
        default = f"{getattr(att_player,'name','Atakujący')} ograł {getattr(def_player,'name','obrońcę')} i ma korytarz do strzału."
        return _safe_choice(base, default)

    @classmethod
    def duel_shot_saved(cls, att_player) -> str:
        base = cls._pack.get("duel_shot_saved")
        default = f"{getattr(att_player,'name','Napastnik')} uderza – golkiper na posterunku!"
        return _safe_choice(base, default)

    # ─────────────────────────────  MICRO-EVENTY (tanie)  ────────────────────────
    @classmethod
    def micro_pass_chain(cls, att, defe) -> str:
        return cls._pick_no_repeat("micro_pass_chain", "Trójkąt podań w bocznym sektorze.")

    @classmethod
    def micro_press(cls, att, defe) -> str:
        return cls._pick_no_repeat("micro_press", "Wysoki pressing, wymuszone zagranie do tyłu.")

    @classmethod
    def micro_throw_in(cls, att) -> str:
        return cls._pick_no_repeat("micro_throw_in", "Aut na wysokości pola karnego – szybko wznawiają.")

    @classmethod
    def micro_goal_kick(cls, defe) -> str:
        return cls._pick_no_repeat("micro_goal_kick", "Wznowienie od bramki, rozgrywają na krótko.")

    @classmethod
    def micro_clearance(cls, att, defe) -> str:
        return cls._pick_no_repeat("micro_clearance", "Wybicie „gdziekolwiek”, ale oddalają zagrożenie.")

    # ─────────────────────────────  KARTKI  ──────────────────────────────────────
    @classmethod
    def yellow(cls, name: str) -> str:
        base = cls._pack.get("yellow")
        return _safe_choice(base, f"🟨 Żółta kartka dla {name}.")

    @classmethod
    def red_card(cls, name: str) -> str:
        base = cls._pack.get("red_card")
        return _safe_choice(base, f"🟥 Czerwona kartka! {name} wylatuje!")

    # ─────────────────────────────  Anti‑repeat helper  ─────────────────────────
    @classmethod
    def _pick_no_repeat(cls, key: str, fallback: str) -> str:
        arr = cls._pack.get(key) or []
        if not arr:
            return fallback
        recent = cls._recent.setdefault(key, [])
        # filtruj ostatnie N; jeśli zabraknie – bierz pełną pulę
        pool = [v for v in arr if v not in recent[-cls._no_repeat_window:]] or arr
        choice = random.choice(pool)
        recent.append(choice)
        return choice

# automatyczne wczytanie pakietu przy imporcie
try:
    Commentary.load()
except Exception:
    # w razie błędu dalej mamy fallbacki
    pass
