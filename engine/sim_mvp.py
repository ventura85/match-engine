from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import random, math, json, re, unicodedata, difflib
from pathlib import Path

# --- Parametry MVP ---
HALF_VMINUTES = 7
STOPPAGE_PER_HALF = (0, 2)
MAX_ACTIONS_PER_MIN = 2
BASE_ACTION_P = 0.35

# --- Synonimy kluczy komentarzy (PL/EN + warianty) ---
SYNONYMS: Dict[str, List[str]] = {
    "announce": ["announce","akcja","ofensywa","offense","build_up","zapowiedz","atak","atak_zapowiedz"],
    "goal": ["goal","gol","bramka","trafienie","brameczka","jedenastka gol"],
    "shot_saved": ["shot_saved","save","strzal_obroniony","strzał_obroniony","interwencja bramkarza"],
    "shot_off": ["shot_off","off_target","strzal_obok","strzał_obok","pudlo","pudło","niecelny"],
    "clearance": ["clearance","wybicie","wykop","wybicie_po_strzale","wybicie po strzale"],
    "throw_in": ["throw_in","aut","wrzut_aut","wrzut z autu","wrzut"],
    "corner_wasted": ["corner_wasted","corner_lost","rog_niewykorzystany","róg niewykorzystany","zmarnowany róg"],
}

DEFAULTS = {
    "announce": ["{team} w ofensywie…"],
    "goal": ["GOL dla {team}!"],
    "shot_saved": ["strzał obroniony"],
    "shot_off": ["strzał obok"],
    "clearance": ["wybicie"],
    "throw_in": ["aut"],
    "corner_wasted": ["róg niewykorzystany"],
}

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s

# === Paczka komentarzy (auto-dopasowanie kluczy + no-repeat) ===
class CommentPack:
    def __init__(self, pack: str = "pl_fun", rng: Optional[random.Random] = None, no_repeat_window: int = 3):
        self.pack = pack
        self.rng = rng or random.Random()
        self.no_repeat_window = no_repeat_window
        self._data: Dict[str, List[str]] = {}
        self._recent: Dict[str, List[str]] = {}
        self._resolved: Dict[str, Optional[str]] = {}
        self._load()

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _candidates(self) -> List[Path]:
        base = self._repo_root() / "assets" / "comments"
        return [
            base / f"{self.pack}.json",
            Path.cwd() / "assets" / "comments" / f"{self.pack}.json",
        ]

    def _load(self) -> None:
        for p in self._candidates():
            if p.is_file():
                d = json.loads(p.read_text(encoding="utf-8"))
                # deduplikacja
                for k, vals in list(d.items()):
                    uniq, seen = [], set()
                    for v in vals:
                        t = (v or "").strip()
                        key = t.lower()
                        if t and key not in seen:
                            seen.add(key); uniq.append(t)
                    d[k] = uniq
                self._data = d
                break
        self._keys_raw = list(self._data.keys())
        self._keys_norm = {_norm(k): k for k in self._keys_raw}
        for kind in SYNONYMS.keys():
            self._resolved[kind] = self._resolve_key(kind)

    def _resolve_key(self, kind: str) -> Optional[str]:
        if not self._keys_raw:
            return None
        norm_keys = list(self._keys_norm.keys())
        # exact
        for syn in SYNONYMS[kind]:
            ns = _norm(syn)
            if ns in self._keys_norm:
                return self._keys_norm[ns]
        # substring/tokens
        for syn in SYNONYMS[kind]:
            ns = _norm(syn); tokens = set(ns.split())
            for nk, orig in self._keys_norm.items():
                if ns in nk or nk in ns: return orig
                if tokens & set(nk.split()): return orig
        # fuzzy
        for syn in SYNONYMS[kind]:
            ns = _norm(syn)
            best = difflib.get_close_matches(ns, norm_keys, n=1, cutoff=0.64)
            if best:
                return self._keys_norm[best[0]]
        return None

    def _pick_from_key(self, key: str, **vars) -> Optional[str]:
        vals = self._data.get(key) or []
        if not vals:
            return None
        recent = self._recent.setdefault(key, [])
        pool = [v for v in vals if v not in recent[-self.no_repeat_window:]] or vals
        txt = self.rng.choice(pool)
        recent.append(txt)
        try:
            return txt.format(**vars)
        except Exception:
            return txt

    def pick(self, kind: str, **vars) -> str:
        key = self._resolved.get(kind)
        if key:
            t = self._pick_from_key(key, **vars)
            if t: return t
        return self.rng.choice(DEFAULTS[kind]).format(**vars)

# === Modele domenowe ===
@dataclass
class Tactic:
    style: str = "balanced"  # 'defensive' | 'balanced' | 'attacking'
    @property
    def action_rate_mod(self) -> float: return {"defensive": 0.92,"balanced": 1.00,"attacking": 1.08}.get(self.style,1.0)
    @property
    def shot_prob_mod(self) -> float:   return {"defensive": 0.95,"balanced": 1.00,"attacking": 1.08}.get(self.style,1.0)
    @property
    def goal_prob_mod(self) -> float:   return {"defensive": 0.95,"balanced": 1.00,"attacking": 1.06}.get(self.style,1.0)

@dataclass
class Player:
    name: str
    pos: str  # GK/DEF/MID/FWD

@dataclass
class TeamCtx:
    name: str
    atk: float = 60.0
    mid: float = 60.0
    deff: float = 60.0
    tactic: Tactic = field(default_factory=Tactic)
    players: List[Player] = field(default_factory=list)

# === ROSTERY ===
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _group_pos(pos_raw: str) -> str:
    p = (pos_raw or "").upper()
    if "GK" in p or "KEEP" in p or "BR" in p: return "GK"
    if any(t in p for t in ["ST","CF","LW","RW","FW","FWD","NAP"]): return "FWD"
    if any(t in p for t in ["CB","LB","RB","DEF","DF","OBR"]): return "DEF"
    return "MID"

def _load_roster_from_json(team_name: str) -> List[Player]:
    p = _repo_root() / "data" / "teams.json"
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
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
            out = []
            for rp in (t.get("players") or []):
                nm = rp.get("name") or rp.get("n") or ""
                pos = rp.get("position") or rp.get("pos") or ""
                if nm:
                    out.append(Player(nm, _group_pos(pos)))
            return out
    return []

def _fallback_roster() -> List[Player]:
    names = [
        ("Jan Kowalski","GK"),
        ("Piotr Nowak","DEF"),("Marek Wiśniewski","DEF"),("Tomasz Kamiński","DEF"),("Krzysztof Lewandowski","DEF"),
        ("Adam Woźniak","MID"),("Michał Dąbrowski","MID"),("Paweł Kozłowski","MID"),
        ("Robert Mazur","FWD"),("Łukasz Jankowski","FWD"),("Wojciech Szymański","FWD"),
    ]
    return [Player(n, p) for n,p in names]

def _ensure_roster(team: TeamCtx) -> None:
    if team.players:
        return
    team.players = _load_roster_from_json(team.name) or _fallback_roster()

def _pick_attacker(team: TeamCtx, rng: random.Random) -> Player:
    pools = [
        [p for p in team.players if p.pos == "FWD"],
        [p for p in team.players if p.pos == "MID"],
        [p for p in team.players if p.pos == "DEF"],
        [p for p in team.players if p.pos == "GK"],
    ]
    for pool in pools:
        if pool:
            return rng.choice(pool)
    return Player(team.name + " Player", "FWD")

def _pick_assister(team: TeamCtx, shooter: Player, rng: random.Random) -> Optional[Player]:
    """Wybór asystenta: priorytet MID, potem FWD, potem DEF; nigdy strzelec ani GK."""
    candidates = (
        [p for p in team.players if p.pos == "MID" and p.name != shooter.name] +
        [p for p in team.players if p.pos == "FWD" and p.name != shooter.name] +
        [p for p in team.players if p.pos == "DEF" and p.name != shooter.name]
    )
    return rng.choice(candidates) if candidates else None

# === Modele prawdopodobieństw ===
def _control_share(a: TeamCtx, b: TeamCtx) -> float:
    a_ctrl = a.mid * 0.6 + a.atk * 0.3 + a.deff * 0.1
    b_ctrl = b.mid * 0.6 + b.atk * 0.3 + b.deff * 0.1
    total = max(a_ctrl + b_ctrl, 1e-6)
    return a_ctrl / total

def _p_shot(att: TeamCtx, deff: TeamCtx) -> float:
    base = 0.55
    ratio = (att.atk / max(deff.deff, 1.0)) ** 0.25
    p = base * (0.8 + 0.2 * ratio)
    p *= att.tactic.shot_prob_mod
    return max(0.25, min(0.85, p))

def _p_goal(att: TeamCtx, deff: TeamCtx) -> float:
    base = 0.12
    ratio = (att.atk / max(deff.deff, 1.0)) ** 0.5
    p = base * (0.8 + 0.2 * ratio)
    p *= att.tactic.goal_prob_mod
    return max(0.04, min(0.35, p))

def _minute_label_str(first_half: bool, vm: int) -> str:
    if vm <= HALF_VMINUTES:
        scaled = math.ceil(vm * 45 / HALF_VMINUTES)
        return (f"{scaled}'" if first_half else f"{45 + max(1, scaled)}'")
    else:
        extra = vm - HALF_VMINUTES
        return f"{'45' if first_half else '90'}+{extra}'"

def _fmt(minute: str, team: str, text: str) -> str:
    return f"{minute} [{team}] {text}"

# === Symulacja ===
def simulate(teamA: TeamCtx, teamB: TeamCtx, seed: int | None = None) -> Dict[str, Any]:
    rng = random.Random(seed)
    comments = CommentPack(pack="pl_fun", rng=rng, no_repeat_window=3)

    # składy do użycia przy strzałach/golach
    _ensure_roster(teamA)
    _ensure_roster(teamB)

    log: List[str] = []
    score = [0, 0]
    shots = [0, 0]
    on_target = [0, 0]

    def sim_half(first_half: bool) -> int:
        controlA = _control_share(teamA, teamB)
        p_action = BASE_ACTION_P
        p_action *= (0.95 + 0.10 * (controlA - 0.5) * 2)
        p_action *= (teamA.tactic.action_rate_mod * controlA + teamB.tactic.action_rate_mod * (1 - controlA))
        p_action = max(0.10, min(0.80, p_action))

        add = rng.randint(*STOPPAGE_PER_HALF)
        vmin_total = HALF_VMINUTES + add

        for vm in range(1, vmin_total + 1):
            minute = _minute_label_str(first_half, vm)
            for _ in range(MAX_ACTIONS_PER_MIN):
                if rng.random() >= p_action:
                    continue
                # kto atakuje
                attA = rng.random() < controlA
                att, deff = (teamA, teamB) if attA else (teamB, teamA)
                idx = 0 if attA else 1

                # (1) zapowiedź
                ann = comments.pick("announce", team=att.name, minute=minute)
                log.append(_fmt(minute, att.name, ann))

                # (2) rezultat
                if rng.random() < _p_shot(att, deff):
                    shots[idx] += 1
                    shooter = _pick_attacker(att, rng)
                    if rng.random() < _p_goal(att, deff):
                        score[idx] += 1
                        on_target[idx] += 1
                        # asysta z prawd. 70%
                        assister_txt = ""
                        if rng.random() < 0.70:
                            assister = _pick_assister(att, shooter, rng)
                            if assister:
                                assister_txt = f"; asysta: {assister.name}"
                            else:
                                assister_txt = "; bez asysty"
                        gtxt = comments.pick("goal", team=att.name, minute=minute, scoreA=score[0], scoreB=score[1])
                        log.append(f"{minute} ⚽ GOL! [{att.name}] {score[0]}:{score[1]} — {gtxt}  (strzelec: {shooter.name}{assister_txt})")
                    else:
                        if rng.random() < 0.6:
                            on_target[idx] += 1
                            rtxt = comments.pick("shot_saved", team=att.name, minute=minute)
                        else:
                            rtxt = comments.pick("shot_off", team=att.name, minute=minute)
                        log.append(_fmt(minute, att.name, f"{rtxt} (uderza {shooter.name})"))
                else:
                    which = rng.random()
                    if which < 0.4:
                        rtxt = comments.pick("throw_in", team=att.name, minute=minute)
                    elif which < 0.8:
                        rtxt = comments.pick("clearance", team=att.name, minute=minute)
                    else:
                        rtxt = comments.pick("corner_wasted", team=att.name, minute=minute)
                    log.append(_fmt(minute, att.name, rtxt))
        return add

    add1 = sim_half(first_half=True)
    log.append(f"HT • Przerwa ({score[0]}:{score[1]}). Doliczono +{add1}'.")
    add2 = sim_half(first_half=False)
    log.append(f"FT • Koniec ({score[0]}:{score[1]}). Doliczono +{add2}'.")

    return {
        "log": log,
        "score": {"A": score[0], "B": score[1]},
        "shots": {"A": shots[0], "B": shots[1]},
        "on_target": {"A": on_target[0], "B": on_target[1]},
        "seed": seed,
    }
