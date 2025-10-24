⚽ Match Engine — .NET + React

Deterministyczny silnik meczu piłkarskiego z lekkim API i przejrzystym frontendem. Budujemy solidną bazę pod grę online: szybki, przewidywalny i łatwy w rozwoju.

🎮 Wizja produktu (skrót)

Świat, w którym prawdziwi ludzie grają główne role (Piłkarz, Manager-Właściciel), kluczowe momenty rozstrzygają interaktywne Live Action Duels, a ekonomia, liga i kariery żyją dzięki decyzjom graczy. Nasz silnik meczowy jest sercem tej wizji. 

Gra piłkarska

🧠 Co budujemy

Deterministyczny RNG: MT19937 + wydzielone strumienie (np. duels, gk_saves, cards, fatigue, setpieces, xg_context, commentary) — zero „przesuwania” seeda między modułami.

Modułowa architektura: Domain, Engine (Match, Minute Simulator + sub-modele), RNG, Reporting.

Raporty: stabilny Schema v1 (rozszerzamy pola, nie łamiemy zgodności).

API + Front: Minimal APIs (/teams, /simulate) i lekki frontend (wynik, statystyki, timeline, „Skrót/Pełna”).

👥 Dane drużyn i graczy — podejście

Teraz (prosto): presety w kodzie (SeedData) — szybki start.

Docelowo (zalecane): pliki JSON w assets/teams/ wczytywane repozytorium danych; łatwe PR-y, wersjonowanie i pełna kontrola.

Opcjonalnie później: SQLite pod ten sam interfejs, gdy zechcemy edytować składy z UI.
👉 Dla deterministyczności trzymamy stałe ID i stabilne sortowanie.

🗺️ Roadmap (M3 → M7)

M3 — Duels + GK
Nowe zdarzenia: DuelWon/Lost, SaveMade; liczniki duels*, saves*. Inwariant: celne = gole + interwencje.

M4 — Sędzia, faule, kartki, SFG
Profile strict/lenient; zdarzenia: Foul, YellowCard, RedCard, FreekickAwarded, PenaltyAwarded.

M5 — Zmęczenie i energia
Tick energii, wpływ na intensywność, pojedynki i skuteczność.

M6 — Stałe fragmenty + xG v2
Playbooki rożnych/wolnych; kontekstowy xG (dystans, kąt, presja, noga, pozycja GK).

M7 — Komentarz i timeline
Kompozytor z cooldownem, różnorodność fraz (PL), sekcja „Kluczowe zdarzenia”.

📊 Standardy jakości

SchemaVersion = 1 — tylko dodajemy pola.

Każdy element losowy = osobny strumień RNG.

Testy: inwarianty, monotoniczność minut (zawsze jest FinalWhistle), testy deterministyczności względem seeda.

Nazewnictwo: EN w kodzie/DTO, PL w UI.

🔧 Jak z tym pracujemy (skrót)

Backend: .NET Minimal APIs, hot-reload lokalnie; CORS dla frontu.

Frontend: Vite/React; statystyki, timeline, tryb „Skrót/Pełna”; polskie formaty.

CI (w planie): build/test Core + API, build frontu, artefakty, analyzers „warn as error”.

🎯 Cel na teraz

Dostarczyć M3 (pojedynki i interwencje GK) z pełnymi inwariantami i widocznością w UI.

Wczytywać drużyny z JSON (presetowe pliki w assets/teams/) przez repozytorium danych.

Utrzymać pełną deterministyczność i kompatybilny raport v1.