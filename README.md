# Football Manager Match Engine ⚽

Modułowy silnik meczowy (Python 3.11) do gry MMO/manager, z naciskiem na taktykę, realizm i czytelny raport meczu. Silnik działa w skali 90’ (symulowane natychmiastowo), a na potrzeby testów utrzymuje skróconą oś czasu 1..10.

## Co potrafi (stan na teraz)

- Model zawodnika: atrybuty fizyczne/techniczne/mentalne; energia i forma wpływają na OVR i przebieg meczu.
- Taktyka: formacja, styl (defensive/balanced/attacking), kanał ataku (wings/center), pressing (low/normal/high), szerokość (narrow/normal/wide).
- Pojedynki (Live Action Duels): kluczowe starcia 1v1 z rezultatem shot/goal/saved/wide; poprawne liczenie strzałów celnych.
- System fauli i kartek: prawdopodobieństwo fauli z taktyki i „agresji” obrońców; żółte/czerwone zależne łagodnie od agresji i decisions zawodnika.
- Profil sędziego: lenient/neutral/strict z mnożnikami na faule i kartki; profil drukowany w CLI i zapisany w raporcie.
- Zmiany zawodników: automatyczne suby (60’ i 75’, max 3) przy ławce; wybór najbardziej zmęczonego i rezerwowego tej samej pozycji; wpływ na siłę drużyny.
- Zmiany taktyczne: podczas przerwy i ok. 70’ zależnie od wyniku (bufory).
- Zmęczenie i dystans: per‑minuta drenaż energii zależny od pozycji, stylu/pressingu/szerokości/kanału oraz udziału w pojedynkach; raport zawiera `player_stats` (energia i `distance_km`).
- Komentarze: mikro (tanie) i makro‑narracje; anty‑karuzela rzutów rożnych.
- Raport: wynik, gole (z asystami), posiadanie, strzały (w tym celne), SFG, faule/kartki, pełny timeline i skrót, profil sędziego, listę zmian, per‑player `distance_km` i energia.
- Testy: 19 zielonych, w tym deterministyczność (seed), struktura raportu, duels/strzały, kartki i profil sędziego.

## Struktura

```
.
├── main.py                 # CLI, druk sędziego, raport, zmiany, dystans
├── engine/
│   ├── match.py           # Silnik: pętla 90’, taktyka, SFG, kary, zmęczenie
│   ├── duel.py            # System pojedynków 1v1
│   ├── comments*.py       # Komentarze
│   └── utils.py
├── models/                # Player/Team
├── data/teams.json        # Przykładowe drużyny
├── scripts/               # batch i matrix do kalibracji
└── tests/                 # testy (pytest)
```

## Uruchomienie

```
pip install -r requirements.txt
python main.py --seed 42 --density high --referee random --timeline all
```

Przydatne flagi:
- `--teamA/--teamB` – wybór drużyn
- `--referee` – `random|lenient|neutral|strict`
- `--verbose` – gęstsze logi
- `--timeline` – `all|last|key|nomicro` (jak drukować chronologię)
- `--timeline-limit` – limit zdarzeń dla trybu `last`

## Batch/Matrix do kalibracji

- `python scripts/run_batch.py` → `reports/batch_stats.csv`
- `python scripts/run_matrix.py` → `reports/matrix.csv` (8×8 presetów)

Analizuj średnie (gole, strzały, faule, kartki, rogi) i koryguj delikatnie stałe w `engine/match.py` jeśli potrzeba.

## Dane zawodników

Minimalny blok atrybutów (przykład w `data/teams.json`):
- Physical: `speed`, `strength`, `stamina`
- Technical: `passing`, `shooting`, `dribbling`, `tackling`, `marking`, `reflexes`, `handling`
- Mental: `positioning`, `concentration`, `decisions`, `aggression` (opcjonalnie; domyślnie 50)

## Oceny pomeczowe (plan)

Kolejny etap: per‑player ratings 1–10 z uwzględnieniem goli/asyst, xG proxy, pojedynków, obron GK, fauli/kartek i pracy bez piłki (distance/work‑rate). Zapis w raporcie i druk Top 3.

## Licencja

Projekt demonstracyjny – swobodny do modyfikacji.
### Atrybuty (skala 1-99)
Rekomendowane zakresy:
- **50-60**: Przeciętny zawodnik
- **60-75**: Dobry zawodnik
- **75-85**: Bardzo dobry zawodnik
- **85-95**: Gwiazda

## Raport z meczu

Po symulacji wyświetlany jest szczegółowy raport zawierający:

1. **Wynik końcowy** z rozbiciem na bramki
2. **Posiadanie piłki** (%)
3. **Strzały** (ogółem i celne)
4. **Analiza taktyczna** - skuteczność strzałów dla każdego stylu gry
5. **Zmiany** - lista wszystkich zmian z powodami
6. **Kluczowe zdarzenia** (gole, obrony, drybling)

## API dla programistów

### Podstawowe użycie w kodzie

```python
from models.team import Team
from models.player import Player
from engine.match import MatchEngine
from engine.utils import set_random_seed

# Załaduj drużyny (lub stwórz manualnie)
team_a = Team(name="Team A", players=[...], formation="4-4-2")
team_b = Team(name="Team B", players=[...], formation="4-3-3")

# Ustaw seed dla powtarzalności (opcjonalnie)
set_random_seed(42)

# Utwórz silnik i symuluj (real_time=False dla szybkiej symulacji)
engine = MatchEngine(team_a, team_b, verbose=True, real_time=False)
report = engine.simulate_match()

# Odczytaj wyniki
print(f"Wynik: {report['score']}")
print(f"Posiadanie: {report['possession']}")
print(f"Bramki: {report['goals']}")
print(f"Zmiany: {report['substitutions']}")
print(f"Wpływ taktyki: {report['tactical_impact']}")
```

## Rozszerzanie projektu

Silnik został zaprojektowany w sposób modułowy, co ułatwia rozbudowę:

### Zaimplementowane funkcje:
- ✅ **Zmiany**: System zmian taktycznych podczas przerwy
- ✅ **Składy przed meczem**: Wyświetlanie pełnych składów z statystykami
- ✅ **Polski komentarz**: Realistyczne komentarze z emotikonami
- ✅ **Analiza taktyczna**: Widoczny wpływ stylu gry na wyniki
- ✅ **10-minutowe mecze**: Szybka symulacja (5+5 min)

### Możliwe rozszerzenia:
- 🔄 **Kontuzje**: Losowe kontuzje zawodników podczas meczu
- 🔄 **Kartki**: Żółte i czerwone kartki z wpływem na grę
- 🔄 **Pełny system zmian**: Ławka rezerwowych i 3 zmiany na drużynę
- 🔄 **Zmęczenie**: Dynamiczne zmniejszanie energy podczas meczu
- 🔄 **Pogoda**: Wpływ warunków pogodowych na grę
- 🔄 **xG (Expected Goals)**: Zaawansowane metryki skuteczności
- 🔄 **Heat mapy**: Wizualizacja pozycji zawodników
- 🔄 **Export**: Eksport raportów do JSON/HTML/PDF
- 🔄 **Aplikacja webowa**: Interfejs w Streamlit lub Flask

## Testowanie

Projekt zawiera suite 12 testów jednostkowych:

```bash
pytest -v
```

Testy sprawdzają:
- ✅ Powtarzalność wyników (seed)
- ✅ Poprawność struktury raportu
- ✅ Walidację wyniku meczu
- ✅ Obliczanie posiadania piłki
- ✅ Statystyki strzałów
- ✅ Wpływ taktyki na wyniki
- ✅ Czas trwania meczu (10 minut)
- ✅ Różnorodność wyników bez seeda
- ✅ Modele Player i Team

## Technologie

- **Python 3.11**
- **Dataclasses** - dla modeli danych
- **Type hints** - pełne typowanie
- **pytest** - framework testowy (12 testów)
- **Tick-based simulation** - 1 tick = 1 minuta
- **Probabilistyczny RNG** - kontrolowana losowość

## Wyniki przykładowe

Przykładowe wyniki 5 kolejnych meczy:
- **Mecz 1**: Blue Hawks 1-0
- **Mecz 2**: Red Lions 1-0
- **Mecz 3**: Remis 0-0 (ze zmianą taktyczną)
- **Mecz 4**: Remis 0-0
- **Mecz 5**: Remis 1-1

Każdy mecz jest inny! 🎲

## Licencja

Projekt edukacyjny - wolny do użytku i modyfikacji.

## Autorzy

Stworzony jako przykładowy projekt demonstracyjny silnika meczowego dla gry football manager.

---

**Dobrej zabawy z symulacją! ⚽🎮**
