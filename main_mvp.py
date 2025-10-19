from __future__ import annotations
import argparse, json, unicodedata, re
from pathlib import Path
from typing import List, Optional, Dict
from engine.sim_mvp import TeamCtx, simulate, Tactic

# --- helpers do składów/konfiguracji (lokalne) ---

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()

def _group_pos(pos_raw: str) -> str:
    p = (pos_raw or "").upper()
    if "GK" in p or "BR" in p or "KEEP" in p: return "GK"
    if any(tag in p for tag in ["CB","LB","RB","DEF","DF","OBR"]): return "DEF"
    if any(tag in p for tag in ["ST","CF","LW","RW","FW","FWD","NAP"]): return "FWD"
    return "MID"

def _load_teams_json() -> Optional[list]:
    p = Path("data/teams.json")
    if not p.is_file(): return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict):
        return data.get("teams") if isinstance(data.get("teams"), list) else [data]
    if isinstance(data, list):
        return data
    return None

def _load_team_entry(team_name: str) -> Optional[Dict]:
    teams = _load_teams_json()
    if not teams: return None
    tnorm = _norm(team_name)
    for t in teams:
        nm = str(t.get("name",""))
        if nm and (_norm(nm) == tnorm or tnorm in _norm(nm)):
            # normalizacja pozycji w players
            players = []
            for rp in (t.get("players") or []):
                nm = rp.get("name") or rp.get("n") or ""
                pos = rp.get("position") or rp.get("pos") or ""
                if nm:
                    players.append({"name": nm, "pos": _group_pos(pos)})
            return {
                "name": nm,
                "style": (t.get("style") or "").lower().strip() or None,
                "ratings": t.get("ratings") or {},
                "players": players
            }
    return None

def _fallback_roster_local() -> List[dict]:
    names = [
        ("Jan Kowalski","GK"),
        ("Piotr Nowak","DEF"),("Marek Wiśniewski","DEF"),("Tomasz Kamiński","DEF"),("Krzysztof Lewandowski","DEF"),
        ("Adam Woźniak","MID"),("Michał Dąbrowski","MID"),("Paweł Kozłowski","MID"),
        ("Robert Mazur","FWD"),("Łukasz Jankowski","FWD"),("Wojciech Szymański","FWD"),
    ]
    return [{"name": n, "pos": p} for n,p in names]

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
    ap.add_argument("--teamA", default="Red")
    ap.add_argument("--teamB", default="Blue")
    ap.add_argument("--styleA", choices=["defensive","balanced","attacking"], default="balanced")
    ap.add_argument("--styleB", choices=["defensive","balanced","attacking"], default="balanced")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--log-json", type=str, default=None)
    ap.add_argument("--quiet", action="store_true")
    return ap.parse_args()

def _ratings_or_default(entry: Optional[Dict]) -> Dict[str,int]:
    r = (entry or {}).get("ratings") or {}
    return {
        "atk": int(r.get("atk", 60)),
        "mid": int(r.get("mid", 60)),
        "def": int(r.get("def", 60)),
    }

def _style_or_default(entry: Optional[Dict], cli_style: str) -> str:
    st = (entry or {}).get("style")
    return st if st in {"defensive","balanced","attacking"} else cli_style

def main():
    args = parse_args()

    # Wczytaj wpisy z teams.json (jeśli są)
    A_entry = _load_team_entry(args.teamA)
    B_entry = _load_team_entry(args.teamB)

    # Składy do wydruku
    rosterA = (A_entry or {}).get("players") or _fallback_roster_local()
    rosterB = (B_entry or {}).get("players") or _fallback_roster_local()

    print("================================================================================")
    print(f"🏟️  ROZPOCZĘCIE MECZU: {args.teamA} vs {args.teamB}")
    print("================================================================================")
    _print_roster(args.teamA, rosterA)
    _print_roster(args.teamB, rosterB)
    print("\n⏱️  MECZ (2×7 min wirtualnych + doliczony) — symulacja natychmiast\n")

    # Styl/taktyka i oceny z pliku (fallback: CLI + 60/60/60)
    A_style = _style_or_default(A_entry, args.styleA)
    B_style = _style_or_default(B_entry, args.styleB)
    A_r = _ratings_or_default(A_entry)
    B_r = _ratings_or_default(B_entry)

    # Zbuduj kontekst drużyn z ocenami + stylem
    A = TeamCtx(args.teamA, atk=A_r["atk"], mid=A_r["mid"], deff=A_r["def"], tactic=Tactic(A_style))
    B = TeamCtx(args.teamB, atk=B_r["atk"], mid=B_r["mid"], deff=B_r["def"], tactic=Tactic(B_style))

    # Symulacja MVP
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
