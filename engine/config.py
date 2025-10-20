"""
Konfiguracja meczu – bez flag CLI.
Zmieniasz wartości tutaj i odpalasz mecz jak zwykle.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Match:
    HALF_VMINUTES: int = 7
    STOPPAGE_PER_HALF: tuple = (0, 2)
    MAX_ACTIONS_PER_MIN: int = 2
    BASE_ACTION_P: float = 0.35

@dataclass(frozen=True)
class SetPieces:
    RATE: float = 0.18
    CORNER_SHARE: float = 0.65

@dataclass(frozen=True)
class Fouls:
    RATE: float = 0.12
    DEFENDERS_BIAS: float = 0.85
    YELLOW_PROB: float = 0.25
    RED_PROB: float = 0.02
    RED_MOD: float = 0.90

@dataclass(frozen=True)
class LiveNarration:
    RATE: float = 0.12

@dataclass(frozen=True)
class LiveDuel:
    MIN: int = 2
    MAX: int = 4
    RATE: float = 0.08  # per-akcja

@dataclass(frozen=True)
class Engagement:
    ON: bool = True
    LEAD_RELAX_EARLY: float = 0.97
    LEAD_RELAX_LATE: float  = 0.94
    TRAIL_PUSH_EARLY: float = 1.03
    TRAIL_PUSH_LATE: float  = 1.08
    RELAX_2PLUS_BONUS: float = 0.98
    PUSH_2PLUS_BONUS: float  = 1.03

@dataclass(frozen=True)
class AntiZero:
    MINUTE: int = 70
    BOOST: float = 1.15

@dataclass(frozen=True)
class Upset:
    """Mikroszansa na niespodziankę – docelowo włączymy w algorytm kontroli."""
    ENABLED: bool = True
    BASE_FLOOR: float = 0.02   # minimalna szansa underdoga
    STRONG_DIFF: float = 25.0  # różnica OVR, od której mocno ścinamy

@dataclass(frozen=True)
class Commentary:
    PACK: str = "pl_fun"

# Zbiorczy uchwyt
class CFG:
    MATCH = Match()
    SET = SetPieces()
    FOULS = Fouls()
    LIVE = LiveNarration()
    DUEL = LiveDuel()
    ENG = Engagement()
    AZ  = AntiZero()
    UPSET = Upset()
    CMT = Commentary()
