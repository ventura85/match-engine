# Football Manager Match Engine ⚽

Profesjonalny silnik meczowy dla gry menedżera piłkarskiego, napisany w Python 3.11.

## Opis projektu

Projekt implementuje kompletny, modułowy silnik symulacji meczów piłkarskich z następującymi funkcjonalnościami:

- **Szczegółowy model zawodników**: Atrybuty fizyczne, techniczne i mentalne
- **Wyświetlanie składów przed meczem**: Pełne składy z statystykami, formą i cechami zawodników
- **Zaawansowana taktyka**: Formacje, style gry (defensive/balanced/attacking), kanały ataku
- **Live Action Duels**: System pojedynków zawodników z probabilistyczną mechaniką
- **10-minutowa symulacja**: Mecz trwa 10 minut (5 min pierwsza połowa + 5 min druga połowa)
- **System zmian**: Zmiany taktyczne podczas przerwy wpływające na formę zawodników
- **Realistyczne komentarze**: Polski komentarz z emotikonami (gole, obrony, drybling)
- **Analiza taktyczna**: Widoczny wpływ stylu gry na skuteczność i statystyki
- **Szczegółowe raporty**: Wydarzenia, statystyki, posiadanie piłki, strzały, zmiany

## Struktura projektu

```
.
├── main.py                 # Główny punkt wejścia
├── requirements.txt        # Zależności Python
├── README.md              # Ten plik
├── replit.md              # Dokumentacja techniczna i user preferences
├── models/                # Modele danych
│   ├── __init__.py
│   ├── player.py         # Model zawodnika
│   └── team.py           # Model drużyny
├── engine/                # Silnik meczowy
│   ├── __init__.py
│   ├── match.py          # Główny silnik symulacji
│   ├── duel.py           # System Live Action Duels
│   └── utils.py          # Funkcje pomocnicze
├── data/                  # Dane
│   └── teams.json        # Przykładowe drużyny
└── tests/                 # Testy
    └── test_match_engine.py
```

## Instalacja i uruchomienie

### 1. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 2. Uruchomienie symulacji

**Podstawowe uruchomienie** (domyślne drużyny):
```bash
python main.py
```

**Z parametrami**:
```bash
python main.py --teamA "Red Lions" --teamB "Blue Hawks" --seed 42 --verbose
```

### 3. Uruchomienie testów

```bash
pytest
```

lub z verbose:
```bash
pytest -v
```

## Parametry CLI

- `--teamA <nazwa>` - Nazwa pierwszej drużyny (domyślnie: "Red Lions")
- `--teamB <nazwa>` - Nazwa drugiej drużyny (domyślnie: "Blue Hawks")
- `--seed <liczba>` - Seed dla generatora losowego (zapewnia powtarzalność wyników)
- `--verbose` - Wyświetla szczegółowe informacje podczas symulacji

## Przykłady użycia

### Przykład 1: Domyślny mecz
```bash
python main.py
```

Wyświetli:
- ⚽ Składy obu drużyn przed meczem
- 🏟️ Przebieg meczu minuta po minucie z komentarzem
- ⏸️ Przerwa (ewentualnie zmiany)
- 🏁 Raport końcowy z analizą taktyczną

### Przykład 2: Powtarzalny wynik
```bash
python main.py --seed 42
# Każde uruchomienie z tym samym seedem da identyczny wynik
```

### Przykład 3: Tryb verbose
```bash
python main.py --verbose
# Pokazuje szczegółowe informacje o pojedynkach i zdarzeniach
```

## Model danych

### Player (Zawodnik)

Każdy zawodnik posiada:
- **Podstawowe**: id, name, position (GK/DEF/MID/FWD)
- **Atrybuty**: 
  - Physical: speed, strength, stamina
  - Technical: passing, shooting, dribbling, tackling, marking, reflexes, handling
  - Mental: positioning, concentration, decisions
- **Stan**: energy (0.7-1.0), form (0.0-1.0)
- **Cechy**: traits (np. 'Ambitious', 'Fast', 'Clinical')

**Wzór Overall Rating**:
```
overall = (0.5 * avg(physical) + 0.35 * avg(technical) + 0.15 * avg(mental)) 
          * form_modifier * energy
```

### Team (Drużyna)

Każda drużyna posiada:
- **Podstawowe**: name, players (lista 11 zawodników)
- **Taktyka**: 
  - formation: np. '4-4-2', '4-3-3'
  - style: 'defensive', 'balanced', 'attacking'
  - attack_channel: 'wings', 'center'

**Modyfikatory stylu**:
- `attacking`: +10% atak, -5% obrona
- `defensive`: -5% atak, +10% obrona
- `balanced`: bez modyfikatorów

## Mechanika silnika

### Symulacja meczu

1. **Tick-based**: Mecz dzieli się na 10 ticków (minut) - 5 na każdą połowę
2. **Wyświetlanie składów**: Przed meczem pokazywane są wszystkie składy z statystykami
3. **Posiadanie piłki**: Określane na podstawie team_control + RNG
4. **Akcje ofensywne**: Prawdopodobieństwo zależne od attack_rating vs defense_rating
5. **Przerwa**: Po 5 minutach mecz się zatrzymuje na przerwę
6. **Zmiany taktyczne**: 30% szans na zmianę podczas przerwy (wpływa na formę zawodnika)
7. **Komentarz**: Polski komentarz z emotikonami dla wszystkich kluczowych akcji

### Komentarze meczowe

Silnik generuje realistyczne komentarze po polsku:
- ⚽⚽⚽ **GOOOOOOL!!!!** - bramki z fajerwerkami
- 🧤 **OBRONA! Wielka parada!** - obronione strzały
- ✨ **Świetny drybling!** - skuteczne dryblingi
- ❌ **Strzela niecelnie!** - nieudane strzały

### Live Action Duels

System pojedynków 1v1:
1. Wybór zawodników (atakujący vs broniący)
2. Losowanie akcji: dribble, pass, shot, tackle
3. Rozstrzygnięcie na podstawie:
   - Atrybuty zawodników
   - Taktyka drużyny
   - Element losowy (RNG)

### Strzały na bramkę

Wieloetapowy proces:
1. **Czy strzał celny?** → zależy od shooting + positioning
2. **Czy będzie gol?** → shooter_rating vs goalkeeper_rating + RNG
3. Możliwe wyniki: goal, shot_saved, shot_off_target, shot_blocked

### System zmian

Podczas przerwy:
- 30% szans na zmianę taktyczną
- Wybierany jest zawodnik z najniższą formą
- Zmiana wpływa na formę zawodnika (zmniejsza do 80%)
- Zmiana jest widoczna w raporcie końcowym

## Konfiguracja drużyn

Drużyny definiuje się w pliku `data/teams.json`:

```json
{
  "teams": [
    {
      "name": "My Team",
      "formation": "4-3-3",
      "style": "attacking",
      "attack_channel": "wings",
      "players": [
        {
          "id": 1,
          "name": "Player Name",
          "position": "GK",
          "attributes": {
            "physical": {"speed": 55, "strength": 70, "stamina": 75},
            "technical": {"reflexes": 85, "handling": 82, "kicking": 68},
            "mental": {"positioning": 84, "concentration": 86, "decisions": 78}
          },
          "energy": 0.95,
          "form": 0.88,
          "traits": ["Calm", "Leader"]
        }
      ]
    }
  ]
}
```

### Pozycje zawodników
- **GK** - Goalkeeper (bramkarz)
- **DEF** - Defender (obrońca)
- **MID** - Midfielder (pomocnik)
- **FWD** - Forward (napastnik)

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
