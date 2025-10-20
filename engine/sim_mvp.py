from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import random, math, json, re, unicodedata
from pathlib import Path
from engine.duel import DuelSystem  # LIVE DUEL

# --- Parametry MVP ---
HALF_VMINUTES = 7
STOPPAGE_PER_HALF = (0, 2)
MAX_ACTIONS_PER_MIN = 2
BASE_ACTION_P = 0.35

# Stałe fragmenty gry (SFG)
SET_PIECE_RATE = 0.18
CORNER_SHARE   = 0.65

# Faule / kartki
FOUL_RATE           = 0.12
FOUL_DEFENDERS_BIAS = 0.85
YELLOW_PROB         = 0.25
RED_PROB            = 0.02
RED_MOD             = 0.90

# Live narracja (kosmetyka)
LIVE_RATE = 0.12

# Live Action Duel
LIVE_DUEL_MIN = 2
LIVE_DUEL_MAX = 4
LIVE_DUEL_RATE = 0.08  # per-akcja, do wyczerpania puli

# --- Zaangażowanie (confidence/determination) ---
ENG_LEAD_RELAX_EARLY = 0.97   # prowadzący do 60'
ENG_LEAD_RELAX_LATE  = 0.94   # prowadzący po 60'
ENG_TRAIL_PUSH_EARLY = 1.03   # przegrywający do 60'
ENG_TRAIL_PUSH_LATE  = 1.08   # przegrywający po 60'
ENG_RELAX_2PLUS_BONUS = 0.98  # ekstra relaks przy +2
ENG_PUSH_2PLUS_BONUS  = 1.03  # ekstra determinacja przy -2

# Anti-zero strzałów
ANTI_ZERO_MINUTE = 70
ANTI_ZERO_BOOST  = 1.15

# --- Synonimy komentarzy (dopasowanie do assets/comments/*.json, fallbacki) ---
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

# === Paczka komentarzy ===
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
        for syn in SYNONYMS[kind]:
            ns = _norm(syn)
            if ns in self._keys_norm:
                return self._keys_norm[ns]
        for syn in SYNONYMS[kind]:
            ns = _norm(syn); tokens = set(ns.split())
            for nk, orig in self._keys_norm.items():
                if ns in nk or nk in ns: return orig
                if tokens & set(nk.split()): return orig
        import difflib as _dif
        for syn in SYNONYMS[kind]:
            ns = _norm(syn)
            best = _dif.get_close_matches(ns, list(self._keys_norm.keys()), n=1, cutoff=0.64)
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

# === Live pack (opcjonalny plik assets/live_actions.json) ===
class LivePack:
    def __init__(self, rng: Optional[random.Random] = None, no_repeat_window: int = 5):
        self.rng = rng or random.Random()
        self.no_repeat_window = no_repeat_window
        self._msgs: List[str] = []
        self._recent: List[str] = []
        self._load()

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _candidates(self) -> List[Path]:
        return [
            self._repo_root() / "assets" / "live_actions.json",
            Path.cwd() / "assets" / "live_actions.json",
        ]

    def _load(self) -> None:
        for p in self._candidates():
            if p.is_file():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        self._msgs = [str(x).strip() for x in data if str(x).strip()]
                    elif isinstance(data, dict):
                        self._msgs = [str(x).strip() for x in data.get("messages", []) if str(x).strip()]
                    break
                except Exception:
                    pass
        if not self._msgs:
            self._msgs = [
                "Trener gestykuluje przy linii.",
                "Kibice głośniejsi – rośnie presja.",
                "Sędzia uspokaja przepychanki.",
                "Drużyna domowa pompuje tempo.",
                "Zmiana ustawienia – bardziej ofensywnie.",
            ]

    def maybe(self) -> Optional[str]:
        if not self._msgs: return None
        pool = [m for m in self._msgs if m not in self._recent[-self.no_repeat_window:]] or self._msgs
        msg = self.rng.choice(pool)
        self._recent.append(msg)
        return msg

# === Modele domenowe ===
@dataclass
class Tactic:
    style: str = "balanced"
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

# wybory graczy
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
    candidates = (
        [p for p in team.players if p.pos == "MID" and p.name != shooter.name] +
        [p for p in team.players if p.pos == "FWD" and p.name != shooter.name] +
        [p for p in team.players if p.pos == "DEF" and p.name != shooter.name]
    )
    return rng.choice(candidates) if candidates else None

def _pick_gk(team: TeamCtx) -> Player:
    gks = [p for p in team.players if p.pos == "GK"]
    return gks[0] if gks else Player("Bramkarz", "GK")

# === Pomoce: rozkład kontroli i prawdopodobieństwa ===
def _control_share_eff(a: TeamCtx, b: TeamCtx, modA: float, modB: float) -> float:
    a_ctrl = (a.mid*modA) * 0.6 + (a.atk*modA) * 0.3 + (a.deff*modA) * 0.1
    b_ctrl = (b.mid*modB) * 0.6 + (b.atk*modB) * 0.3 + (b.deff*modB) * 0.1
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

def _clamp(v: float, lo=30.0, hi=95.0) -> float:
    return max(lo, min(hi, v))

# syntetyczne atrybuty do DuelSystem
def _synth_attrs(team: TeamCtx, p: Player) -> Dict[str, float]:
    tA, tM, tD = team.atk, team.mid, team.deff
    name = p.name
    if p.pos == "GK":
        return {
            "name": name,
            "reflexes":   _clamp(55 + 0.60*tD),
            "handling":   _clamp(55 + 0.55*tD),
            "positioning":_clamp(50 + 0.45*tD),
            "concentration":_clamp(50 + 0.50*tD),
            "speed":      _clamp(45 + 0.30*tD),
            "tackling":   _clamp(40 + 0.20*tD),
            "marking":    _clamp(40 + 0.20*tD),
            "shooting":   _clamp(35 + 0.10*tA),
            "stamina":    _clamp(65 + 0.30*tD, hi=100),
            "decisions":  _clamp(50 + 0.45*tM),
            "dribbling":  40.0,
            "passing":    _clamp(45 + 0.35*tM),
        }
    if p.pos == "FWD":
        return {
            "name": name,
            "shooting":   _clamp(50 + 0.60*tA),
            "dribbling":  _clamp(48 + 0.50*tA),
            "passing":    _clamp(45 + 0.40*tM),
            "speed":      _clamp(50 + 0.50*tA),
            "decisions":  _clamp(45 + 0.50*tM),
            "positioning":_clamp(48 + 0.50*tA),
            "stamina":    _clamp(60 + 0.30*((tA+tM)/2), hi=100),
            "reflexes":   45.0, "handling": 45.0, "marking": 40.0, "tackling": 40.0, "concentration": _clamp(45 + 0.35*tM)
        }
    if p.pos == "MID":
        return {
            "name": name,
            "dribbling":  _clamp(48 + 0.45*tM),
            "passing":    _clamp(50 + 0.55*tM),
            "shooting":   _clamp(45 + 0.35*tA),
            "speed":      _clamp(48 + 0.40*tM),
            "decisions":  _clamp(48 + 0.55*tM),
            "positioning":_clamp(48 + 0.45*tM),
            "stamina":    _clamp(65 + 0.35*tM, hi=100),
            "reflexes":   45.0, "handling": 45.0, "marking": _clamp(45 + 0.35*tD), "tackling": _clamp(45 + 0.35*tD), "concentration": _clamp(45 + 0.45*tM)
        }
    # DEF
    return {
        "name": name,
        "tackling":    _clamp(50 + 0.55*tD),
        "marking":     _clamp(50 + 0.55*tD),
        "positioning": _clamp(48 + 0.50*tD),
        "speed":       _clamp(45 + 0.35*tD),
        "concentration":_clamp(48 + 0.50*tD),
        "reflexes":    _clamp(45 + 0.20*tD),
        "handling":    _clamp(45 + 0.20*tD),
        "shooting":    _clamp(40 + 0.20*tA),
        "dribbling":   _clamp(42 + 0.25*tM),
        "passing":     _clamp(45 + 0.35*tM),
        "decisions":   _clamp(45 + 0.40*tM),
        "stamina":     _clamp(65 + 0.35*tD, hi=100),
    }

# === Statystyki indywidualne do ocen ===
def _init_player_stats(team: TeamCtx) -> Dict[str, Dict[str, float]]:
    s: Dict[str, Dict[str, float]] = {}
    for p in team.players:
        s[p.name] = dict(goals=0, assists=0, shots=0, on_target=0, saves=0, fouls=0, yc=0, rc=0, duel_plus=0, duel_minus=0, pos=p.pos)
    return s

def _bump(d: Dict[str, Dict[str, float]], name: str, key: str, val: float = 1.0):
    if name not in d: d[name] = dict(goals=0,assists=0,shots=0,on_target=0,saves=0,fouls=0,yc=0,rc=0,duel_plus=0,duel_minus=0,pos="MID")
    d[name][key] = d[name].get(key,0) + val

def _compute_ratings(team: TeamCtx, stats: Dict[str, Dict[str, float]], goals_conceded: int) -> List[Tuple[str, float, Dict[str,float]]]:
    out = []
    for p in team.players:
        st = stats.get(p.name, {})
        g  = st.get("goals",0); a = st.get("assists",0)
        sh = st.get("shots",0); sot = st.get("on_target",0)
        sv = st.get("saves",0)
        fl = st.get("fouls",0); yc = st.get("yc",0); rc = st.get("rc",0)
        dp = st.get("duel_plus",0); dm = st.get("duel_minus",0)
        base = 6.0
        base += 0.9*g + 0.5*a + 0.1*sot
        base += 0.2*sv
        base += 0.2*dp - 0.1*dm
        base -= 0.05*fl + 0.3*yc + 1.0*rc
        if p.pos in ("GK","DEF"):
            base -= 0.05*goals_conceded
        base = max(4.0, min(10.0, round(base,1)))
        out.append((p.name, base, st))
    return out

# === Symulacja ===
def simulate(teamA: TeamCtx, teamB: TeamCtx, seed: int | None = None) -> Dict[str, Any]:
    rng = random.Random(seed)
    comments = CommentPack(pack="pl_fun", rng=rng, no_repeat_window=3)
    livepack = LivePack(rng=rng, no_repeat_window=5)

    _ensure_roster(teamA)
    _ensure_roster(teamB)

    log: List[str] = []
    score = [0, 0]
    shots = [0, 0]
    on_target = [0, 0]
    fouls_t = [0, 0]
    yc_t = [0, 0]
    rc_t = [0, 0]
    mod = [1.0, 1.0]  # osłabienie po czerwonej: A,B
    live_duel_left = rng.randint(LIVE_DUEL_MIN, LIVE_DUEL_MAX)

    # indywidualne staty do ocen
    pstatsA = _init_player_stats(teamA)
    pstatsB = _init_player_stats(teamB)

    anti_zero_used = [False, False]  # czy już aktywowaliśmy boost

    def _add_goal_line(minute: str, att_team_name: str, idx: int, sp_tag: str = "", shooter: Optional[str]=None, assister: Optional[str]=None):
        tag = f" {sp_tag}" if sp_tag else ""
        extra = ""
        if shooter:
            extra = f"  (strzelec: {shooter}"
            if assister is not None:
                extra += f"; asysta: {assister if assister else 'bez asysty'}"
            extra += ")"
        log.append(f"{minute} ⚽ GOL! [{att_team_name}] {score[0]}:{score[1]} — Krótki rozbieg i chłodna głowa – gol!{tag}{extra}")

    def _apply_engagement(idx: int, minute_real: int, p_action: float, p_sh: float, p_gl: float) -> Tuple[float,float,float]:
        late = minute_real >= 60
        att_lead = score[idx] - score[1-idx]
        if att_lead >= 1:
            m = ENG_LEAD_RELAX_LATE if late else ENG_LEAD_RELAX_EARLY
            if att_lead >= 2: m *= ENG_RELAX_2PLUS_BONUS
            p_action *= m; p_sh *= m; p_gl *= m
        elif att_lead <= -1:
            m = ENG_TRAIL_PUSH_LATE if late else ENG_TRAIL_PUSH_EARLY
            if att_lead <= -2: m *= ENG_PUSH_2PLUS_BONUS
            p_action *= m; p_sh *= m; p_gl *= m
        return p_action, p_sh, p_gl

    def _resolve_live_duel(minute: str, minute_real: int, attA: bool) -> bool:
        nonlocal live_duel_left, score, shots, on_target
        if live_duel_left <= 0: 
            return False
        if rng.random() >= LIVE_DUEL_RATE:
            return False

        live_duel_left -= 1

        att, deff = (teamA, teamB) if attA else (teamB, teamA)
        idx = 0 if attA else 1

        # wybór typu duelu
        duel_type = rng.choices(["dribble","pass","shoot","penalty"], weights=[0.35,0.25,0.30,0.10])[0]

        # wybór graczy
        if duel_type == "penalty":
            attacker = _pick_attacker(att, rng)
            if attacker.pos == "DEF":
                attacker = _pick_attacker(att, rng)
            gk = _pick_gk(deff)
            a_attrs = _synth_attrs(att, attacker)
            d_attrs = _synth_attrs(deff, gk)
            a_act = rng.choice(["penalty_left","penalty_right","penalty_center"])
            d_act = rng.choice(["gk_dive_left","gk_dive_right","gk_stay"])
            header = f"🎮 LIVE DUEL: karny — {attacker.name} vs {gk.name} ({a_act} vs {d_act})"
            defender_name = gk.name
        else:
            attacker = _pick_attacker(att, rng)
            defender = _pick_gk(deff) if duel_type == "shoot" and rng.random() < 0.8 else _pick_attacker(deff, rng)
            a_attrs = _synth_attrs(att, attacker)
            d_attrs = _synth_attrs(deff, defender)
            if duel_type == "dribble":
                a_act = "dribble"; d_act = rng.choices(["press","tackle","block"], weights=[0.4,0.4,0.2])[0]
            elif duel_type == "pass":
                a_act = "pass"; d_act = rng.choices(["press","tackle","block"], weights=[0.35,0.25,0.40])[0]
            else:
                a_act = "shoot"; d_act = rng.choices(["gk_close","gk_stay","gk_block"], weights=[0.5,0.3,0.2])[0]
            header = f"🎮 LIVE DUEL: {attacker.name} vs {defender.name} ({a_act} vs {d_act})"
            defender_name = defender.name

        log.append(_fmt(minute, att.name, header))
        res = DuelSystem.resolve(a_attrs, d_attrs, a_act, d_act, rng=rng)
        for c in res.get("commentary", []):
            log.append(_fmt(minute, att.name, c + " (LIVE DUEL)"))

        # statystyki / wynik + pstats
        oc = res.get("outcome")
        if oc in ("goal","shot_saved","shot_wide"):
            shots[idx] += 1
            _bump(pstatsA if idx==0 else pstatsB, attacker.name, "shots", 1)
        if oc in ("goal","shot_saved"):
            on_target[idx] += 1
            _bump(pstatsA if idx==0 else pstatsB, attacker.name, "on_target", 1)
            if oc == "shot_saved" and ("gk" in d_act or duel_type=="penalty"):
                _bump(pstatsB if idx==0 else pstatsA, defender_name, "saves", 1)

        if oc == "goal":
            score[idx] += 1
            _bump(pstatsA if idx==0 else pstatsB, attacker.name, "goals", 1)
            _bump(pstatsA if idx==0 else pstatsB, attacker.name, "duel_plus", 1)
            _add_goal_line(minute, att.name, idx, sp_tag=" [z LIVE DUEL]", shooter=attacker.name, assister=None)
        elif oc in ("breakthrough","key_pass"):
            _bump(pstatsA if idx==0 else pstatsB, attacker.name, "duel_plus", 0.5)
        elif oc in ("intercept","shot_saved"):
            _bump(pstatsB if idx==0 else pstatsA, defender_name, "duel_plus", 0.5)
        elif oc in ("lost","shot_wide"):
            _bump(pstatsA if idx==0 else pstatsB, attacker.name, "duel_minus", 0.5)
        elif oc == "foul":
            _bump(pstatsB if idx==0 else pstatsA, defender_name, "fouls", 1)

        return True

    def sim_half(first_half: bool) -> int:
        add = rng.randint(*STOPPAGE_PER_HALF)
        vmin_total = HALF_VMINUTES + add

        for vm in range(1, vmin_total + 1):
            minute = _minute_label_str(first_half, vm)
            # real minute (1..90+): licz bez parsowania stringa
            if vm <= HALF_VMINUTES:
                scaled = math.ceil(vm * 45 / HALF_VMINUTES)
                minute_real = scaled if first_half else 45 + max(1, scaled)
            else:
                extra = vm - HALF_VMINUTES
                minute_real = (45 if first_half else 90) + extra

            controlA = _control_share_eff(teamA, teamB, mod[0], mod[1])
            lead = score[0] - score[1]  # >0: A prowadzi

            for _ in range(MAX_ACTIONS_PER_MIN):
                # LIVE DUEL
                attA = (rng.random() < controlA)
                if _resolve_live_duel(minute, minute_real, attA):
                    continue

                # szansa na standardową akcję
                p_action = BASE_ACTION_P
                p_action *= (0.95 + 0.10 * (controlA - 0.5) * 2)
                p_action *= (teamA.tactic.action_rate_mod * controlA + teamB.tactic.action_rate_mod * (1 - controlA))
                p_action = max(0.10, min(0.80, p_action))

                # kto atakuje
                attA = rng.random() < controlA
                att, deff = (teamA, teamB) if attA else (teamB, teamA)
                idx = 0 if attA else 1
                opp = 1 - idx

                # zaangażowanie
                p_sh = _p_shot(att, deff)
                p_gl = _p_goal(att, deff)
                p_action, p_sh, p_gl = _apply_engagement(idx, minute_real, p_action, p_sh, p_gl)

                # anti-zero po 70' dla przegrywającego
                if minute_real >= ANTI_ZERO_MINUTE and score[idx] < score[opp] and shots[idx] == 0 and not anti_zero_used[idx]:
                    p_sh *= ANTI_ZERO_BOOST

                p_sh = max(0.15, min(0.90, p_sh))
                p_gl = max(0.03, min(0.40, p_gl))

                if rng.random() >= p_action:
                    continue

                sp_kind = None  # 'corner' | 'freekick' | None

                # 1) FAUL?
                if rng.random() < FOUL_RATE:
                    def_fouls = rng.random() < FOUL_DEFENDERS_BIAS
                    fouler_idx = opp if def_fouls else idx
                    fouls_t[fouler_idx] += 1
                    foul_team = teamA.name if fouler_idx == 0 else teamB.name

                    # przypisz winnego (do ocen)
                    if def_fouls:
                        pool = [p for p in (teamB.players if idx==0 else teamA.players) if p.pos in ("DEF","MID")] or (teamB.players if idx==0 else teamA.players)
                        fouler = rng.choice(pool)
                        _bump(pstatsB if idx==0 else pstatsA, fouler.name, "fouls", 1)
                    else:
                        pool = [p for p in (teamA.players if idx==0 else teamB.players) if p.pos in ("FWD","MID")] or (teamA.players if idx==0 else teamB.players)
                        fouler = rng.choice(pool)
                        _bump(pstatsA if idx==0 else pstatsB, fouler.name, "fouls", 1)

                    log.append(_fmt(minute, foul_team, "✋ Faul"))

                    r = rng.random()
                    if r < RED_PROB:
                        rc_t[fouler_idx] += 1
                        mod[fouler_idx] *= RED_MOD
                        _bump(pstatsA if fouler_idx==0 else pstatsB, fouler.name, "rc", 1)
                        log.append(_fmt(minute, foul_team, "🟥 Czerwona kartka!"))
                    elif r < RED_PROB + YELLOW_PROB:
                        yc_t[fouler_idx] += 1
                        _bump(pstatsA if fouler_idx==0 else pstatsB, fouler.name, "yc", 1)
                        log.append(_fmt(minute, foul_team, "🟨 Żółta kartka"))

                    sp_kind = "freekick"
                    if not def_fouls:
                        att, deff = deff, att
                        idx, opp = opp, idx
                    log.append(_fmt(minute, att.name, "🎯 Rzut wolny"))

                # 2) SFG / zapowiedź
                if sp_kind is None:
                    if rng.random() < SET_PIECE_RATE:
                        sp_kind = "corner" if rng.random() < CORNER_SHARE else "freekick"
                        log.append(_fmt(minute, att.name, "🏳️ Rzut rożny")) if sp_kind == "corner" else log.append(_fmt(minute, att.name, "🎯 Rzut wolny"))
                    else:
                        ann = comments.pick("announce", team=att.name, minute=minute)
                        log.append(_fmt(minute, att.name, ann))

                # 3) Rezultat
                if rng.random() < p_sh:
                    shots[idx] += 1
                    if minute_real >= ANTI_ZERO_MINUTE and shots[idx] == 1:
                        anti_zero_used[idx] = True
                    shooter = _pick_attacker(att, rng)
                    _bump(pstatsA if idx==0 else pstatsB, shooter.name, "shots", 1)

                    if rng.random() < p_gl:
                        score[idx] += 1
                        on_target[idx] += 1
                        _bump(pstatsA if idx==0 else pstatsB, shooter.name, "on_target", 1)
                        _bump(pstatsA if idx==0 else pstatsB, shooter.name, "goals", 1)
                        assister = None
                        if rng.random() < 0.70:
                            assister = _pick_assister(att, shooter, rng)
                            if assister:
                                _bump(pstatsA if idx==0 else pstatsB, assister.name, "assists", 1)
                        tag = "po rzucie rożnym" if sp_kind == "corner" else ("po rzucie wolnym" if sp_kind == "freekick" else "z akcji")
                        _add_goal_line(minute, att.name, idx, sp_tag=f"  ({tag})", shooter=shooter.name, assister=(assister.name if assister else None))
                    else:
                        if rng.random() < 0.6:
                            on_target[idx] += 1
                            _bump(pstatsA if idx==0 else pstatsB, shooter.name, "on_target", 1)
                            gk = _pick_gk(deff)
                            _bump(pstatsB if idx==0 else pstatsA, gk.name, "saves", 1)
                            rtxt = comments.pick("shot_saved", team=att.name, minute=minute)
                        else:
                            rtxt = comments.pick("shot_off", team=att.name, minute=minute)
                        extra = " po SFG" if sp_kind else ""
                        log.append(_fmt(minute, att.name, f"{rtxt}{extra} (uderza {shooter.name})"))
                else:
                    if sp_kind == "corner":
                        rtxt = comments.pick("corner_wasted", team=att.name, minute=minute)
                        log.append(_fmt(minute, att.name, rtxt))
                    elif sp_kind == "freekick":
                        log.append(_fmt(minute, att.name, "wolny niewykorzystany"))
                    else:
                        which = rng.random()
                        if which < 0.4:
                            rtxt = comments.pick("throw_in", team=att.name, minute=minute)
                        elif which < 0.8:
                            rtxt = comments.pick("clearance", team=att.name, minute=minute)
                        else:
                            rtxt = comments.pick("corner_wasted", team=att.name, minute=minute)
                        log.append(_fmt(minute, att.name, rtxt))

            # 5) Live action (kosmetyka)
            if rng.random() < LIVE_RATE:
                msg = livepack.maybe()
                if msg:
                    log.append(f"{minute} 🟢 LIVE: {msg}")

        return add

    add1 = sim_half(first_half=True)
    log.append(f"HT • Przerwa ({score[0]}:{score[1]}). Doliczono +{add1}'.")
    add2 = sim_half(first_half=False)
    log.append(f"FT • Koniec ({score[0]}:{score[1]}). Doliczono +{add2}'.")

    # === OCENY 1–10 ===
    ratingsA = _compute_ratings(teamA, pstatsA, goals_conceded=score[1])
    ratingsB = _compute_ratings(teamB, pstatsB, goals_conceded=score[0])

    log.append("⭐ OCENY PIŁKARZY (1–10)")
    log.append(f"   {teamA.name}:")
    for name, rate, st in ratingsA:
        log.append(f"      - {name}: {rate}  [G:{int(st['goals'])} A:{int(st['assists'])} SOT:{int(st['on_target'])} SV:{int(st['saves'])} YC:{int(st['yc'])} RC:{int(st['rc'])}]")
    log.append(f"   {teamB.name}:")
    for name, rate, st in ratingsB:
        log.append(f"      - {name}: {rate}  [G:{int(st['goals'])} A:{int(st['assists'])} SOT:{int(st['on_target'])} SV:{int(st['saves'])} YC:{int(st['yc'])} RC:{int(st['rc'])}]")

    return {
        "log": log,
        "score": {"A": score[0], "B": score[1]},
        "shots": {"A": shots[0], "B": shots[1]},
        "on_target": {"A": on_target[0], "B": on_target[1]},
        "fouls": {"A": fouls_t[0], "B": fouls_t[1]},
        "cards": {"A": {"yellow": yc_t[0], "red": rc_t[0]}, "B": {"yellow": yc_t[1], "red": rc_t[1]}},
        "seed": seed,
        "ratings": { "A": ratingsA, "B": ratingsB },
    }
