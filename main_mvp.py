from __future__ import annotations
import argparse, json, unicodedata, re
from pathlib import Path
from typing import List, Tuple
from engine.sim_mvp import TeamCtx, simulate, Tactic

# --- helpers do wyświetlenia składów (lokalne; nie importujemy nic więcej) ---

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()

def _group_pos(pos_raw: str) -> str:
    p = (pos_raw or "").upper()
    if "GK" in p or "BR" in p or "KEEP" in p:
        return "GK"
    if any(tag in p for tag in ["CB","LB","RB","DEF","DF","OBR"]):
        return "DEF"
    if any(tag in p for tag in ["ST","CF","LW","RW","FW","FWD","NAP"]):
        return "FWD"
    return "MID"

def _load_roster_from_json_local(team_name: str):
    """
    Minimalne wczytanie składu z data/teams.json (jeśli istnieje).
    Oczekuje pól 'name' i listy 'players' z kluczem 'name' i 'pos'/'position'.
    """
    p = Path("data/teams.json")
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

    teams = []
    if isinstance(data, dict):
        teams = data.get("teams") if isinstance(data.get("teams"), list) else [data]
    elif isinstance(data, list):
        teams = data

    tnorm = _norm(team_name)
    for t in teams:
        nm = str(t.get("name",""))
        if not nm: 
            continue
        if _norm(nm) == tnorm or tnorm in _norm(nm):
            players = t.get("players") or []
            out = []
            for rp in players:
                nm = rp.get("name") or rp.get("n") or ""
                pos = rp.get("position") or rp.get("pos") or ""
                if nm:
                    out.append({"name": nm, "pos": _group_pos(pos)})
            return out
    return None

def _fallback_roster_local() -> List[dict]:
    """Ten sam zestaw nazwisk co w fallbacku silnika (żeby się zgadzało)."""
    names = [
        ("Jan Kowalski","GK"),
        ("Piotr Nowak","DEF"),("Marek Wiśniewski","DEF"),("Tomasz Kamiński","DEF"),("Krzysztof Lewandowski","DEF"),
        ("Adam Woźniak","MID"),("Michał Dąbrowski","MID"),("Paweł Kozłowski","MID"),
        ("Robert Mazur","FWD"),("Łukasz Jankowski","FWD"),("Wojciech Szymański","FWD"),
    ]
    return [{"name": n, "pos": p} for n,p in names]

def _load_roster_any(team_name: str) -> List[dict]:
    return _load_roster_from_json_local(team_name) or _fallback_roster_local()

def _print_roster(title: str, roster: List[dict]) -> None:
    gk  = [p["name"] for p in roster if p.get("pos") == "GK"]
    defs= [p["name"] for p in roster if p.get("pos") == "DEF"]
    mids= [p["name"] for p in roster if p.get("pos") == "MID"]
    fwds= [p["name"] for p in roster if p.get("pos") == "FWD"]

    print(f"\n🔹 {title}")
    if gk:   print("   Bramkarz: " + ", ".join(gk))
    if defs: print("   Obrońcy:  " + ", ".join(defs))
    if mids: print("   Pomocnicy: " + ", ".join(mids))
    if fwds: print("   Napastnicy: " + ", ".join(fwds))

# --- CLI ---

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teamA", default="Red Lions")
    ap.add_argument("--teamB", default="Blue Hawks")
    ap.add_argument("--styleA", choices=["defensive","balanced","attacking"], default="balanced")
    ap.add_argument("--styleB", choices=["defensive","balanced","attacking"], default="balanced")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--log-json", type=str, default=None)
    ap.add_argument("--quiet", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()

    # Składy (druk tylko informacyjny; silnik ma własny fallback i też użyje teams.json jeśli zbieżny)
    rosterA = _load_roster_any(args.teamA)
    rosterB = _load_roster_any(args.teamB)

    print("================================================================================")
    print(f"🏟️  ROZPOCZĘCIE MECZU: {args.teamA} vs {args.teamB}")
    print("================================================================================")
    _print_roster(args.teamA, rosterA)
    _print_roster(args.teamB, rosterB)
    print("\n⏱️  MECZ (2×7 min wirtualnych + doliczony) — symulacja natychmiast\n")

    # Symulacja MVP
    A = TeamCtx(args.teamA, tactic=Tactic(args.styleA))
    B = TeamCtx(args.teamB, tactic=Tactic(args.styleB))
    report = simulate(A, B, seed=args.seed)

    if not args.quiet:
        for line in report["log"]:
            print(line)
        sa, sb = report["shots"]["A"], report["shots"]["B"]
        ota, otb = report["on_target"]["A"], report["on_target"]["B"]
        sca, scb = report["score"]["A"], report["score"]["B"]
        print(f"\n[RECAP] Wynik: {sca}:{scb}  |  Strzały: A {sa} ({ota} celnych) / B {sb} ({otb} celnych)")

    if args.log_json:
        with open(args.log_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[i] Zapisano: {args.log_json}")

if __name__ == "__main__":
    main()
