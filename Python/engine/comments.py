from __future__ import annotations
import random
from typing import Dict


def format_names(text: str, context: Dict[str, str]) -> str:
    """
    Zamienia {name}, {att}, {def} na dostarczone w kontekście.
    Braki zastępuje neutralnymi słowami i usuwa pozostawione klamry.
    """
    rep = {
        'name': context.get('name') or context.get('att') or 'zawodnik',
        'att': context.get('att') or 'atakujący',
        'def': context.get('def') or 'obrońca',
    }
    out = text or ''
    for k, v in rep.items():
        out = out.replace('{' + k + '}', str(v))
    if '{' in out or '}' in out:
        import re as _re
        out = _re.sub(r"[{}]", "", out)
    return out


class Commentary:
    """
    Zestaw krótkich, gotowych komentarzy meczowych.
    Wszystkie metody zwracają już sformatowany tekst (PL + emoji),
    bez minut – minutę dokleja warstwa wyżej.
    """

    # ———— START / BANERY ————
    @staticmethod
    def kickoff() -> str:
        return "Rozpoczynamy! Pierwszy gwizdek sędziego i gramy!"

    # ———— MIKRO-KOMENTARZE / TŁO ————
    @staticmethod
    def switch_height() -> str:
        return "Zmienna wysokość ataku, wachlowanie piłką – czekają na lukę."

    @staticmethod
    def triangle_side() -> str:
        return "Trójkąt podań w bocznym sektorze."

    @staticmethod
    def short_throw() -> str:
        return "Krótki wrzut i od razu gra."

    @staticmethod
    def gk_build() -> str:
        return "Wznowienie od bramki, rozgrywają na krótko."

    @staticmethod
    def safe_clear() -> str:
        return "Wybicie „gdziekolwiek”, ale oddalają zagrożenie."

    @staticmethod
    def high_press_back() -> str:
        return "Wysoki pressing, wymuszone zagranie do tyłu."

    @staticmethod
    def one_touch() -> str:
        return "Gra na jeden kontakt – płynie."

    @staticmethod
    def lock_options() -> str:
        return "Zamykają kierunki podań – rywal bez opcji."

    @staticmethod
    def slowdown() -> str:
        return "Zamiast szarży – rozsądek. Przepychają piłkę w bezpiecznych sektorach, rytm celowo stłumiony."

    @staticmethod
    def body_language(team_name: str) -> str:
        # delikatny wariant narracyjny z nazwą drużyny
        pool = [
            f"Body language mówi wszystko – {team_name} idzie po swoje, rywal gasi pożary.",
            f"Kibice {team_name} podrywają się z miejsc – narasta presja.",
            f"{team_name} wygląda na pewnych siebie – gra pod kontrolą.",
        ]
        return random.choice(pool)

    # ———— SFG ————
    @staticmethod
    def corner_for(team_name: str) -> str:
        # sam opis „kornera”; minuta i ewentualna dogrywka jest wyżej
        tail = random.choice([
            "Blok jak mur – korner.",
            "Świetna parada na róg!",
            "Strzał zablokowany – będzie róg!",
        ])
        return f"🏳️ Rzut rożny dla {team_name}! {tail}"

    @staticmethod
    def free_kick() -> str:
        tail = random.choice([
            "Rzut wolny – dorzucą w szesnastkę?",
            "Stały fragment – ustawiają murek.",
        ])
        return tail

    # ———— POJEDYNKI 1v1 ————
    @staticmethod
    def duel_won(text: str) -> str:
        # Otrzymujemy już zewnętrznie zbudowany tekst (z nazwiskami),
        # tylko dodajemy ikonki i lekki akcent.
        return f"⚔️ ✨ {text}"

    @staticmethod
    def duel_lost(text: str) -> str:
        return f"⚔️ 🚫 {text}"

    # ———— AKCJE OGÓLNE ————
    @staticmethod
    def will_cross_or_shoot() -> str:
        return "Będzie wrzutka czy strzał?"

    @staticmethod
    def keep_patience() -> str:
        return "Krótka klepka, cierpliwe budowanie."

    # ———— BRAMKARSKIE ————
    @staticmethod
    def gk_save() -> str:
        return "🧤 Piłka zmierzała w okienko – wyłapana."

    @staticmethod
    def on_target_generic(player_name: str | None = None) -> str:
        if player_name:
            return f"🧤 {player_name} celnie – dobra interwencja bramkarza!"
        return "🧤 Celny strzał – bramkarz na miejscu."

    @staticmethod
    def off_target_generic(player_name: str | None = None) -> str:
        if player_name:
            return f"❌ {player_name} niecelnie!"
        return "❌ Niecelnie!"
