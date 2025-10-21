from __future__ import annotations
from typing import List
import random
from .comments_repo_mvp import CommentsRepoMVP

# Mapujemy zdarzenia na możliwe klucze w paczce (z fallbackami)
KEYS = {
    "announce": ["announce", "offense", "akcja", "build_up"],
    "shot_saved": ["shot_saved", "save", "strzal_obroniony"],
    "shot_off": ["shot_off", "off_target", "strzal_obok"],
    "clearance": ["clearance", "wybicie", "def_clear"],
    "throw_in": ["throw_in", "aut", "wrzut_aut"],
    "corner_wasted": ["corner_wasted", "corner_lost", "rog_niewykorzystany"],
    "goal": ["goal", "gol"],
    # Makro-narracje (dłuższe bloki)
    "macro_build": ["build_up_long", "build_up_rich", "macro_build"],
    "pressure": ["pressure", "wysoki_pressing", "napor"],
    "momentum": ["momentum_shift", "momentum", "zmiana_momentum"],
    "endgame": ["endgame_drama", "koncowka_dramat", "drama"],
    "calm": ["calm_down", "uspokojenie", "kontrola_tempo"],
}

DEFAULTS = {
    "announce": ["• {team} w ofensywie…"],
    "shot_saved": ["⛔ Strzał obroniony."],
    "shot_off": ["❌ Strzał obok."],
    "clearance": ["🧹 Wybicie."],
    "throw_in": ["↔️ Aut."],
    "corner_wasted": ["🪣 Róg niewykorzystany."],
    "goal": ["⚽ GOL! {team} prowadzi {scoreA}:{scoreB}."],
    # Dłuższe bloki – 2–3 zdania każdy (fallbacki)
    "macro_build": [
        "{team} uspokaja grę krótkimi podaniami. {minute}' – piłka krąży od nogi do nogi, rywal biega za cieniem. Publiczność wyczuwa, że to preludium do czegoś konkretnego.",
        "Długie posiadanie {team}, bez wymuszeń. Po cierpliwym rozegraniu pojawia się przestrzeń między liniami – łapią rytm i pewność."],
    "pressure": [
        "{team} dociąża pressingiem, zamykają rywala głęboko. Dośrodkowanie – wybite, ale piłka wraca i narasta presja w defensywie.",
        "Kolejne fale ataku {team}. Druga piłka zawsze ich, trybuny podrywają się – to może być moment przełomowy."],
    "momentum": [
        "Po chwili chaosu – przełamanie. {team} zaczyna dyktować warunki: dwa szybkie ataki, rośnie tempo i odwaga z piłką.",
        "Zmiana akcentów: {team} przejmuje inicjatywę, rywal tylko gasi pożary. Wabią na jedną stronę, by uderzyć po drugiej."],
    "endgame": [
        "Końcówka tej odsłony i robi się gęsto. Każdy kontakt na granicy faulu, każdy aut na wagę złota – wszyscy liczą sekundy.",
        "Ostatnie chwile i adrenalina na maksie. W polu karnym iskrzy – teraz liczy się charakter i zimna krew."],
    "calm": [
        "Gra zwalnia – {team} trzyma piłkę i czeka na błąd. Świadome zarządzanie tempem, żeby odzyskać oddech i kontrolę.",
        "Zamiast szarży – rozsądek. {team} przepycha piłkę w bezpiecznych sektorach, rytm celowo stłumiony."],
}


class Comments:
    def __init__(self, pack: str = "pl_fun", lang: str = "pl", no_repeat_window: int = 3):
        self.repo = CommentsRepoMVP(lang=lang, pack=pack, no_repeat_window=no_repeat_window)
        self.repo.load()
        # Użyj globalnego RNG (seedowanego przez set_random_seed) dla powtarzalności narracji
        self.repo.rng = random

    def _pick(self, kind: str, **kw) -> str:
        for key in KEYS[kind]:
            t = self.repo.pick(key, **kw)
            if t:
                return t
        # fallback tekst
        import random
        return random.choice(DEFAULTS[kind]).format(**kw)

    # API używane przez silnik (krótkie/mikro)
    def announce(self, *, team: str, minute: str) -> str:
        return self._pick("announce", team=team, minute=minute)

    def goal(self, *, team: str, minute: str, scoreA: int, scoreB: int) -> str:
        return self._pick("goal", team=team, minute=minute, scoreA=scoreA, scoreB=scoreB)

    def shot_saved(self, *, team: str, minute: str) -> str:
        return self._pick("shot_saved", team=team, minute=minute)

    def shot_off(self, *, team: str, minute: str) -> str:
        return self._pick("shot_off", team=team, minute=minute)

    def clearance(self, *, team: str, minute: str) -> str:
        return self._pick("clearance", team=team, minute=minute)

    def throw_in(self, *, team: str, minute: str) -> str:
        return self._pick("throw_in", team=team, minute=minute)

    def corner_wasted(self, *, team: str, minute: str) -> str:
        return self._pick("corner_wasted", team=team, minute=minute)

    # Dłuższe, rzadziej emitowane komentarze (makro‑narracje)
    def macro(self, kind: str, **kw) -> str:
        """Zwraca dłuższy blok narracji dla danego rodzaju sytuacji.

        kind: jedna z {"macro_build", "pressure", "momentum", "endgame", "calm"}
        """
        return self._pick(kind, **kw)
