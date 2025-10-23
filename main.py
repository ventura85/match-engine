from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List
from models.player import Player
from models.team import Team
from engine.match import MatchEngine, TOTAL_SIM_MINUTES, DEFAULT_REAL_MINUTES
from engine.utils import set_random_seed

DATA_DIR = Path(__file__).parent / "data"
TEAMS_JSON = DATA_DIR / "teams.json"

# Wymuś wyjście UTF-8 w konsoli (zapobiega krzaczeniu polskich znaków)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def render_lineups(team_a: Team, team_b: Team) -> None:
    print("\n" + "=" * 80)
    print("⚽ SKŁADY DRUŻYN ⚽")
    print("=" * 80 + "\n")

    def _mean(d: Dict[str, float]) -> float:
        return sum(d.values()) / max(1, len(d)) if d else 0.0

    def ov(p: Player) -> str:
        try:
            attrs = getattr(p, "attributes", {}) or {}
            ph = attrs.get("physical", {}) or {}
            te = attrs.get("technical", {}) or {}
            me = attrs.get("mental", {}) or {}
            avg = 0.5 * _mean(ph) + 0.35 * _mean(te) + 0.15 * _mean(me)
            avg *= getattr(p, "form", 1.0) * getattr(p, "energy", 1.0)
            return f"{avg:.1f}"
        except Exception:
            return "?"

    def print_team(team: Team, icon: str) -> None:
        print(f"{icon} {team.name}")
        print(
            f"   Formacja: {getattr(team,'formation','4-4-2')} | Styl: {getattr(team,'style','balanced')} | Atak: {getattr(team,'attack_channel','center')}\n"
        )
        print("   Skład:\n")

        groups = {
            "Bramkarz": [p for p in team.players if (p.position or "").upper() == "GK"],
            "Obrońcy": [p for p in team.players if (p.position or "").upper() == "DEF"],
            "Pomocnicy": [p for p in team.players if (p.position or "").upper() == "MID"],
            "Napastnicy": [p for p in team.players if (p.position or "").upper() == "FWD"],
        }
        for title, arr in groups.items():
            if not arr:
                continue
            print(f"   {title}:")
            for pl in arr:
                traits = ", ".join(getattr(pl, "traits", [])[:2]) if getattr(pl, "traits", None) else ""
                traits_txt = f" | Cechy: {traits}" if traits else ""
                print(
                    f"      # {pl.name:<22} | Overall: {ov(pl):>5} | Forma: {getattr(pl,'form',1.0):.2f}{traits_txt}"
                )
            print()

    print_team(team_a, "🔴")
    print_team(team_b, "🔵")
    print("=" * 80 + "\n")


def load_teams() -> Dict[str, Team]:
    if not TEAMS_JSON.exists():
        print(f"[BŁĄD] Brak pliku z danymi: {TEAMS_JSON}")
        sys.exit(1)
    try:
        data = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[BŁĄD] Nie udało się wczytać {TEAMS_JSON}: {e}")
        sys.exit(1)

    teams: Dict[str, Team] = {}
    for t in data.get("teams", []):
        name = t.get("name", "Unknown Team")
        formation = t.get("formation", "4-4-2")
        style = t.get("style", "balanced")
        attack_channel = t.get("attack_channel", "center")
        players: List[Player] = []
        for p in t.get("players", []):
            players.append(
                Player(
                    id=p.get("id", 0),
                    name=p.get("name", "Anon"),
                    position=p.get("position", "MID"),
                    attributes=p.get("attributes", {"physical": {}, "technical": {}, "mental": {}}),
                    energy=p.get("energy", 1.0),
                    form=p.get("form", 1.0),
                    traits=p.get("traits", []),
                )
            )
        pressing = t.get("pressing", "normal")
        width = t.get("width", "normal")
        teams[name] = Team(
            name=name,
            players=players,
            formation=formation,
            style=style,
            attack_channel=attack_channel,
            pressing=pressing,
            width=width,
        )
    if not teams:
        print("[BŁĄD] Nie znaleziono żadnych drużyn w teams.json.")
        sys.exit(1)
    return teams


def print_match_report(report: Dict, *, timeline_mode: str = "all", timeline_limit: int = 120) -> None:
    print("\n" + "=" * 70)
    print(f"RAPORT Z MECZU: {report['team_a']} vs {report['team_b']}")
    print("=" * 70 + "\n")
    print(f"📊 WYNIK KOŃCOWY: {report['team_a']} {report['score_a']} - {report['score_b']} {report['team_b']}\n")

    if report["goals_a"] or report["goals_b"]:
        print("⚽ BRAMKI:")
        for g in report["goals_a"]:
            assist = f" (asysta: {g['assist']})" if g["assist"] else ""
            print(f"   {report['team_a']}: {g['minute']}' {g['scorer']}{assist}")
        for g in report["goals_b"]:
            assist = f" (asysta: {g['assist']})" if g["assist"] else ""
            print(f"   {report['team_b']}: {g['minute']}' {g['scorer']}{assist}")
    else:
        print("⚽ BRAMKI: Brak bramek w tym meczu")

    st = report["stats"]
    print("\n📈 STATYSTYKI:")
    print(
        f"   Posiadanie piłki:\n      {report['team_a']}: {st['possession_a']}%\n      {report['team_b']}: {st['possession_b']}%"
    )
    print(
        f"\n   Strzały:\n      {report['team_a']}: {st['shots_a']} ({st['shots_on_a']} celnych)\n      {report['team_b']}: {st['shots_b']} ({st['shots_on_b']} celnych)"
    )

    # Pojedynki (z totals; fallback na same 'won' gdyby ktoś odpalił starszy match.py)
    duels_tot_a = st.get("duels_total_a", st.get("duels_won_a", 0))
    duels_tot_b = st.get("duels_total_b", st.get("duels_won_b", 0))

    # xG (prosty agregat)
    xg_a = st.get("xg_a", report.get("xg_a", 0.0))
    xg_b = st.get("xg_b", report.get("xg_b", 0.0))

    print(
        f"\n   Pojedynki (wygrane/łącznie):\n      {report['team_a']}: {st['duels_won_a']}/{duels_tot_a}\n      {report['team_b']}: {st['duels_won_b']}/{duels_tot_b}"
    )
    print(
        f"\n   Stałe fragmenty:\n      Rogi: {report['team_a']}: {st['corners_a']}  |  {report['team_b']}: {st['corners_b']}\n"
        f"      Wolne: {report['team_a']}: {st['freekicks_a']}  |  {report['team_b']}: {st['freekicks_b']}\n"
        f"      Karne: {report['team_a']}: {st['penalties_a']}  |  {report['team_b']}: {st['penalties_b']}"
    )
    print(f"\n   xG:\n      {report['team_a']}: {xg_a:.2f}\n      {report['team_b']}: {xg_b:.2f}")

    print(
        f"\n   Faule i kartki:\n      Faule: {report['team_a']}: {st['fouls_a']}  |  {report['team_b']}: {st['fouls_b']}\n"
        f"      Żółte: {report['team_a']}: {st['yellows_a']}  |  {report['team_b']}: {st['yellows_b']}\n"
        f"      Czerwone: {report['team_a']}: {st['reds_a']}  |  {report['team_b']}: {st['reds_b']}"
    )

    # Zmiany
    subs = report.get("substitutions") or []
    if subs:
        print("\nZMIANY:")
        for s in subs:
            print(f"   {s['minute']}' {s['team']}: {s['out']} -> {s['in']} ({s.get('reason','')})")

    # Dystans – Top 3 per team (jeśli dostępne)
    pstats = report.get("player_stats") or {}
    for team_name in (report["team_a"], report["team_b"]):
        plist = pstats.get(team_name) or []
        if not plist:
            continue
        top = sorted(plist, key=lambda x: x.get("distance_km", 0.0), reverse=True)[:3]
        print(f"\n📏 DYSTANS – {team_name} (Top 3):")
        for it in top:
            print(f"   {it['name']:<22} {it['distance_km']:>4.2f} km | energia {it['energy']:.2f}")

    # Kluczowe zdarzenia
    important_types = {
        "goal",
        "goal_penalty",
        "goal_freekick",
        "corner",
        "penalty_miss",
        "red_card",
        "stoppage_time",
        "final_whistle",
    }
    events_src = report.get("events_full") or report["events"]
    important = [e for e in events_src if e["event_type"] in important_types]
    if important:
        print("\nKLUCZOWE ZDARZENIA:")
        for e in important[:20]:
            print(f"   {e['description']}")

    # Timeline wg trybu
    timeline = [e for e in events_src if e["event_type"] not in ("banner", "info")]
    if timeline_mode == "key":
        timeline = [e for e in timeline if e["event_type"] in important_types]
        title = "CHRONOLOGIA (kluczowe)"
    elif timeline_mode == "nomicro":
        timeline = [e for e in timeline if e["event_type"] != "micro"]
        title = "CHRONOLOGIA (bez mikro)"
    elif timeline_mode == "last":
        timeline = timeline[-max(1, int(timeline_limit)) :]
        title = f"CHRONOLOGIA (ostatnie {max(1, int(timeline_limit))})"
    else:
        title = "CHRONOLOGIA (pełna)"

    if timeline:
        print(f"\n{title}:")
        for e in timeline:
            print(f"   {e['description']}")

    print("\n" + "=" * 80 + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--teamA", type=str)
    p.add_argument("--teamB", type=str)
    p.add_argument("--seed", type=int)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--real-time", action="store_true")
    p.add_argument("--real-minutes", type=int, default=DEFAULT_REAL_MINUTES)
    p.add_argument(
        "--density",
        type=str,
        default="high",
        choices=["low", "med", "high"],
        help="Gęstość mikro-komentarzy (bez 'ultra').",
    )
    p.add_argument(
        "--referee",
        type=str,
        default="random",
        choices=["random", "lenient", "neutral", "strict"],
        help="Profil sędziego: random/lenient/neutral/strict",
    )
    p.add_argument(
        "--timeline",
        type=str,
        default="all",
        choices=["all", "last", "key", "nomicro"],
        help="Tryb wyświetlania timeline w CLI",
    )
    p.add_argument("--timeline-limit", type=int, default=120, help="Limit zdarzeń dla trybu 'last'")
    # Zapis JSON raportu (domyślnie włączony)
    p.add_argument(
        "--save-json",
        dest="save_json",
        type=lambda v: str(v).lower() not in ("0", "false", "no"),
        default=True,
        help="Czy zapisać raport do pliku JSON (domyślnie True)",
    )
    p.add_argument(
        "--json-path",
        type=str,
        default=str((Path("out") / "last_report.json").resolve()),
        help="Ścieżka docelowa pliku JSON (domyślnie out/last_report.json)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed is not None:
        try:
            set_random_seed(args.seed)
        except Exception:
            pass

    teams = load_teams()
    team_a_name = args.teamA or list(teams.keys())[0]
    default_b = next((n for n in teams.keys() if n != team_a_name), None) or list(teams.keys())[0]
    team_b_name = args.teamB or default_b
    if team_a_name not in teams:
        print(f"[UWAGA] Nie znaleziono '{team_a_name}' – używam domyślnej.")
        team_a_name = list(teams.keys())[0]
    if team_b_name not in teams:
        print(f"[UWAGA] Nie znaleziono '{team_b_name}' – używam innej niż A.")
        team_b_name = next((n for n in teams.keys() if n != team_a_name), list(teams.keys())[0])

    team_a = teams[team_a_name]
    team_b = teams[team_b_name]

    # Nagłówek
    print("\n⚽ FOOTBALL MANAGER - MATCH ENGINE")
    print(f"   Mecz: {team_a.name} vs {team_b.name}\n   Czas trwania: {TOTAL_SIM_MINUTES} SYMULACJI (bez czekania)\n")

    # Składy
    render_lineups(team_a, team_b)

    # Silnik
    engine = MatchEngine(
        team_a,
        team_b,
        verbose=bool(args.verbose),
        real_time=bool(args.real_time),
        real_minutes_target=int(args.real_minutes),
        density=args.density,
        referee_profile=args.referee,
    )

    # Sędzia (profil)
    try:
        ref = engine.referee
        print(f"Sędzia: {ref.get('label','Neutralny')} (profil: {ref.get('key','neutral')})\n")
    except Exception:
        pass

    # Symulacja + raport
    report = engine.simulate_match()
    print_match_report(report, timeline_mode=args.timeline, timeline_limit=args.timeline_limit)

    # Zapis JSON (jeśli włączony)
    try:
        if bool(getattr(args, "save_json", True)):
            out_path = Path(getattr(args, "json_path", str(Path("out") / "last_report.json")))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    main()
