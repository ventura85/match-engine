# engine package initializer
# Nie importujemy nic "na siłę", żeby uniknąć pętli/cieniowania błędów importu.
# Eksporty trzymamy leniwie — konsument i tak używa: `from engine.match import MatchEngine`

__all__ = [
    "match",
    "events",
    "duel",
    "fatigue",
    "config",
    "utils",
    "comments",
]
