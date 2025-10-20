from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import random, math, json, re, unicodedata
from pathlib import Path
from engine.duel import DuelSystem
from engine.config import CFG  # konfiguracja

# --- CONFIG (bezpieczne fallbacki, gdy brak pól w CFG) ---
def _get(ns, key, default): return getattr(ns, key, default) if ns else default

MATCH = getattr(CFG, "MATCH", None)
SET   = getattr(CFG, "SET", None)
FOULS = getattr(CFG, "FOULS", None)
LIVE  = getattr(CFG, "LIVE", None)
DUEL  = getattr(CFG, "DUEL", None)
ENG   = getattr(CFG, "ENG", None)
AZ    = getattr(CFG, "AZ", None)
CMT   = getattr(CFG, "CMT", None)
FAT   = getattr(CFG, "FATIGUE", None)

HALF_VMINUTES       = _get(MATCH, "HALF_VMINUTES", 14)     # 2x7 min wirtualnych
STOPPAGE_PER_HALF   = tuple(_get(MATCH, "STOPPAGE_PER_HALF", (0,2)))
MAX_ACTIONS_PER_MIN = _get(MATCH, "MAX_ACTIONS_PER_MIN", 2)
BASE_ACTION_P       = _get(MATCH, "BASE_ACTION_P", 0.35)

SET_PIECE_RATE      = _get(SET, "RATE", 0.18)
CORNER_SHARE        = _get(SET, "CORNER_SHARE", 0.55)

FOUL_RATE           = _get(FOULS, "RATE", 0.12)
FOUL_DEFENDERS_BIAS = _get(FOULS, "DEFENDERS_BIAS", 0.7)
YELLOW_PROB         = _get(FOULS, "YELLOW_PROB", 0.25)
RED_PROB            = _get(FOULS, "RED_PROB", 0.02)
RED_MOD             = _get(FOULS, "RED_MOD", 0.86)

LIVE_RATE           = _get(LIVE, "RATE", 0.25)
LIVE_DUEL_MIN       = _get(DUEL, "MIN", 1)
LIVE_DUEL_MAX       = _get(DUEL, "MAX", 3)
LIVE_DUEL_RATE0     = _get(DUEL, "RATE", 0.18)

ENG_ON                = _get(ENG, "ON", True)
ENG_LEAD_RELAX_EARLY  = _get(ENG, "LEAD_RELAX_EARLY", 0.96)
ENG_LEAD_RELAX_LATE   = _get(ENG, "LEAD_RELAX_LATE", 0.93)
ENG_TRAIL_PUSH_EARLY  = _get(ENG, "TRAIL_PUSH_EARLY", 1.04)
ENG_TRAIL_PUSH_LATE   = _get(ENG, "TRAIL_PUSH_LATE", 1.08)
ENG_RELAX_2PLUS_BONUS = _get(ENG, "RELAX_2PLUS_BONUS", 0.98)
ENG_PUSH_2PLUS_BONUS  = _get(ENG, "PUSH_2PLUS_BONUS", 1.03)

ANTI_ZERO_MINUTE    = _get(AZ, "MINUTE", 70)
ANTI_ZERO_BOOST     = _get(AZ, "BOOST", 1.35)

CMT_PACK            = _get(CMT, "PACK", "pl_fun")

# --- FATIGUE (model) ---
FAT_ON             = _get(FAT, "ON", True)
FAT_BASE_PER_MIN   = _get(FAT, "BASE_PER_MIN", 0.6)      # bazowy spadek / min dla zawodnika
FAT_TEMPO_FACTOR   = _get(FAT, "TEMPO_FACTOR", {"defensive":0.95,"balanced":1.0,"attacking":1.10})
FAT_PRESS_FACTOR   = _get(FAT, "PRESS_FACTOR", {"defensive":0.95,"balanced":1.0,"attacking":1.06})
FAT_EVENT_BONUS    = _get(FAT, "EVENT_BONUS", 2.0)       # udział w akcji (strzał/SFG)
FAT_DUEL_BONUS     = _get(FAT, "DUEL_BONUS", 3.5)        # udział w LIVE DUEL
FAT_GK_BASE_FACTOR = _get(FAT, "GK_BASE_FACTOR", 0.4)    # GK mniej się męczy bazowo
FAT_EFFECT_MIN     = _get(FAT, "EFFECT_MIN", 0.85)       # dolna granica wpływu zmęczenia na skuteczność
FAT_LOW_THRESHOLD  = _get(FAT, "LOW_THRESHOLD", 55)      # poniżej tego wzrasta ryzyko faulu
FAT_LOW_FOUL_BOOST = _get(FAT, "LOW_FOUL_BOOST", 0.40)   # do +40% FOUL_RATE przy skrajnie niskiej stam.

# --- Komentarze (synonimy + fallback) ---
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

class CommentPack:
    def __init__(self, pack: str = CMT_PACK, rng: Optional[random.Random] = None, no_repeat_window: int = 3):
        self.pack = pack
        self.rng = rng or random.Random()
        self.no_repeat_window = no_repeat_window
        self._data: Dict[str, List[str]] = {}
        self._recent: Dict[str, List[str]] = {}
        self._resolved: Dict[str, Optional[str]] = {}
        self._load()
    def _repo_root(self) -> Path: return Path(__file__).resolve().parents[1]
    def _candidates(self) -> List[Path]:
        base = self._repo_root() / "assets" / "comments"
        return [base / f"{self.pack}.json", Path.cwd() / "assets" / "comments" / f"{self.pack}.json"]
    def _load(self) -> None:
        for p in self._candidates():
            if p.is_file():
                d = json.loads(p.read_text(encoding="utf-8"))
                for k, vals in list(d.items()):
                    uniq, seen = [], set()
                    for v in vals:
                        t = (v or "").strip(); key = t.lower()
                        if t and key not in seen: seen.add(key); uniq.append(t)
                    d[k] = uniq
                self._data = d; break
        self._keys_raw = list(self._data.keys())
        self._keys_norm = {_norm(k): k for k in self._keys_raw}
        for kind in SYNONYMS.keys():
            self._resolved[kind] = self._resolve_key(kind)
    def _resolve_key(self, kind: str) -> Optional[str]:
        if not self._keys_raw: return None
        for syn in SYNONYMS[kind]:
            ns = _norm(syn)
            if ns in self._keys_norm: return self._keys_norm[ns]
        for syn in SYNONYMS[kind]:
            ns = _norm(syn); tokens = set(ns.split())
            for nk, orig in self._keys_norm.items():
                if ns in nk or nk in ns: return orig
                if tokens & set(nk.split()): return orig
        import difflib as _dif
        for syn in SYNONYMS[kind]:
            ns = _norm(syn); best = _dif.get_close_matches(ns, list(self._keys_norm.keys()), n=1, cutoff=0.64)
            if best: return self._keys_norm[best[0]]
        return None
    def _pick_from_key(self, key: str, **vars) -> Optional[str]:
        vals = self._data.get(key) or []
        if not vals: return None
        recent = self._recent.setdefault(key, [])
        pool = [v for v in vals if v not in recent[-self.no_repeat_window:]] or vals
        txt = self.rng.choice(pool); recent.append(txt)
        try: return txt.format(**vars)
        except Exception: return txt
    def pick(self, kind: str, **vars) -> str:
        key = self._resolved.get(kind)
        if key:
            t = self._pick_from_key(key, **vars)
            if t: return t
        return self.rng.choice(DEFAULTS[kind]).format(**vars)

class LivePack:
    def __init__(self, rng: Optional[random.Random] = None, no_repeat_window: int = 5):
        self.rng = rng or random.Random()
        self.no_repeat_window = no_repeat_window
        self._msgs: List[str] = []; self._recent: List[str] = []
        self._load()
    def _repo_root(self) -> Path: return Path(__file__).resolve().parents[1]
    def _candidates(self) -> List[Path]:
        return [self._repo_root() / "assets" / "live_actions.json", Path.cwd() / "assets" / "live_actions.json"]
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
                except Exception: pass
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
        msg = self.rng.choice(pool); self._recent.append(msg); return msg

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

def _repo_root() -> Path: return Path(__file__).resolve().parents[1]
def _group_pos(pos_raw: str) -> str:
    p = (pos_raw or "").upper()
    if "GK" in p or "KEEP" in p or "BR" in p: return "GK"
    if any(t in p for t in ["ST","CF","LW","RW","FW","FWD","NAP"]): return "FWD"
    if any(t in p for t in ["CB","LB","RB","DEF","DF","OBR"]): return "DEF"
    return "MID"

def _load_roster_from_json(team_name: str) -> List[Player]:
    p = _repo_root() / "data" / "teams.json"
    if not p.is_file(): return []
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
        nm = str(t.get("name", ""))
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

def _fallback_rooster() -> List[Player]:
    names = [
        ("Jan Kowalski","GK"),
        ("Piotr Nowak","DEF"),("Marek Wiśniewski","DEF"),("Tomasz Kamiński","DEF"),("Krzysztof Lewandowski","DEF"),
        ("Adam Woźniak","MID"),("Michał Dąbrowski","MID"),("Paweł Kozłowski","MID"),
        ("Robert Mazur","FWD"),("Łukasz Jankowski","FWD"),("Wojciech Szymański","FWD"),
    ]
    return [Player(n, p) for n,p in names]

def _ensure_roster(team: TeamCtx) -> None:
    if not team.players:
        team.players = _load_roster_from_json(team.name) or _fallback_rooster()

def _pick_attacker(team: TeamCtx, rng: random.Random) -> Player:
    pools = [
        [p for p in team.players if p.pos == "FWD"],
        [p for p in team.players if p.pos == "MID"],
        [p for p in team.players if p.pos == "DEF"],
        [p for p in team.players if p.pos == "GK"],
    ]
    for pool in pools:
        if pool: return rng.choice(pool)
    return Player(team.name + " Player", "FWD")

def _pick_assister(team: TeamCtx, shooter: Player, rng: random.Random) -> Optional[Player]:
    candidates = ([p for p in team.players if p.pos == "MID" and p.name != shooter.name] +
                  [p for p in team.players if p.pos == "FWD" and p.name != shooter.name] +
                  [p for p in team.players if p.pos == "DEF" and p.name != shooter.name])
    return rng.choice(candidates) if candidates else None

def _pick_gk(team: TeamCtx) -> Player:
    gks = [p for p in team.players if p.pos == "GK"]
    return gks[0] if gks else Player("Bramkarz", "GK")

# ---------------- FATIGUE UTILS ----------------
def _stam_init(team: TeamCtx) -> Dict[str, float]:
    # start od indywidualnej „stamina” z profilu, max 100
    out = {}
    for p in team.players:
        base = 70.0
        if p.pos == "GK": base = 75.0
        # prosta zależność od atrybutów drużyny (im lepsza, tym lepsza kondycja bazowa)
        if p.pos == "FWD": base += (team.atk - 60) * 0.5
        elif p.pos == "MID": base += (team.mid - 60) * 0.5
        else: base += (team.deff - 60) * 0.5
        out[p.name] = max(50.0, min(100.0, base))
    return out

def _avg_stam(stam: Dict[str,float], pos_map: Dict[str,str], only: Optional[str]=None) -> float:
    names = [n for n in stam if (only is None or pos_map.get(n)==only)]
    if not names: return 100.0
    return sum(stam[n] for n in names) / len(names)

def _drain(stam: Dict[str,float], who: List[str], amount: float):
    for n in who:
        if n in stam:
            stam[n] = max(0.0, stam[n] - amount)

def _drain_base(stam: Dict[str,float], style: str, pos_map: Dict[str,str]):
    if not FAT_ON: return
    tempo = FAT_TEMPO_FACTOR.get(style, 1.0)
    press = FAT_PRESS_FACTOR.get(style, 1.0)
    base = FAT_BASE_PER_MIN * tempo * press
    for n,v in list(stam.items()):
        is_gk = pos_map.get(n) == "GK"
        stam[n] = max(0.0, v - (base * (FAT_GK_BASE_FACTOR if is_gk else 1.0)))

def _fatigue_factor(avg_stam: float) -> float:
    # mapuje 0..100 -> [FAT_EFFECT_MIN .. 1.0]
    return FAT_EFFECT_MIN + (1.0 - FAT_EFFECT_MIN) * (avg_stam/100.0)

# ---------------- RESZTA NARZĘDZI ----------------
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

@dataclass
class PlayerStats:
    goals: int = 0; assists: int = 0; shots: int = 0; on_target: int = 0; saves: int = 0
    fouls: int = 0; yc: int = 0; rc: int = 0; duel_plus: float = 0.0; duel_minus: float = 0.0; pos: str = "MID"

def _init_player_stats(team: TeamCtx) -> Dict[str, Dict[str, float]]:
    s: Dict[str, Dict[str, float]] = {}
    for p in team.players:
        s[p.name] = dict(goals=0, assists=0, shots=0, on_target=0, saves=0, fouls=0, yc=0, rc=0, duel_plus=0, duel_minus=0, pos=p.pos)
    return s

def _bump(d: Dict[str, Dict[str, float]], name: str, key: str, val: float = 1.0):
    if name not in d:
        d[name] = dict(goals=0,assists=0,shots=0,on_target=0,saves=0,fouls=0,yc=0,rc=0,duel_plus=0,duel_minus=0,pos="MID")
    d[name][key] = d[name].get(key,0) + val

def _compute_ratings(team: TeamCtx, stats: Dict[str, Dict[str, float]], goals_conceded: int) -> List[Tuple[str, float, Dict[str,float]]]:
    out = []
    for p in team.players:
        st = stats.get(p.name, {})
        g,a,sh,sot,sv = st.get("goals",0), st.get("assists",0), st.get("shots",0), st.get("on_target",0), st.get("saves",0)
        fl,yc,rc = st.get("fouls",0), st.get("yc",0), st.get("rc",0)
        dp,dm = st.get("duel_plus",0), st.get("duel_minus",0)
        base = 6.0
        base += 0.9*g + 0.5*a + 0.1*sot
        base += 0.2*sv
        base += 0.2*dp - 0.1*dm
        base -= 0.05*fl + 0.3*yc + 1.0*rc
        if p.pos in ("GK","DEF"): base -= 0.05*goals_conceded
        base = max(4.0, min(10.0, round(base,1)))
        out.append((p.name, base, st))
    return out

def simulate(teamA: TeamCtx, teamB: TeamCtx, seed: int | None = None) -> Dict[str, Any]:
    rng = random.Random(seed)
    comments = CommentPack(pack=CMT_PACK, rng=rng, no_repeat_window=3)
    livepack = LivePack(rng=rng, no_repeat_window=5)

    _ensure_roster(teamA); _ensure_roster(teamB)

    # pozycje (do GK itp.)
    posA = {p.name: p.pos for p in teamA.players}
    posB = {p.name: p.pos for p in teamB.players}

    # stamina per player
    stamA = _stam_init(teamA)
    stamB = _stam_init(teamB)

    log: List[str] = []
    score = [0, 0]
    shots = [0, 0]
    on_target = [0, 0]
    fouls_t = [0, 0]
    yc_t = [0, 0]
    rc_t = [0, 0]
    mod = [1.0, 1.0]
    live_duel_left = rng.randint(LIVE_DUEL_MIN, LIVE_DUEL_MAX)
    duels_done = 0
    last_duel_minute = None  # cooldown 1 „tick” (ta sama minuta)

    # xG i posiadanie
    xg = [0.0, 0.0]
    pos_ticks = [0.0, 0.0]

    # indywidualne staty
    pstatsA = _init_player_stats(teamA)
    pstatsB = _init_player_stats(teamB)

    anti_zero_used = [False, False]

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
        if not ENG_ON: return p_action, p_sh, p_gl
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

    def _apply_fatigue_effects(idx_att: int, p_action: float, p_sh: float, p_gl: float) -> Tuple[float,float,float]:
        if not FAT_ON: return p_action, p_sh, p_gl
        atk_stam_avg = _avg_stam(stamA, posA) if idx_att == 0 else _avg_stam(stamB, posB)
        def_stam_avg = _avg_stam(stamB, posB) if idx_att == 0 else _avg_stam(stamA, posA)
        f_atk = _fatigue_factor(atk_stam_avg)         # 0.85..1.0
        wear_def = (100.0 - def_stam_avg) / 100.0     # im bardziej zmęczona obrona, tym łatwiej o gol
        p_action *= f_atk
        p_sh *= f_atk
        p_gl *= f_atk * (1.0 + 0.12 * wear_def)       # do +12% gdy obrona wyjechana
        return p_action, p_sh, p_gl

    def _live_duel_rate(minute_real: int, idx_att: int) -> float:
        rate = LIVE_DUEL_RATE0
        lead = score[idx_att] - score[1-idx_att]
        if minute_real >= 60:
            if lead < 0:
                rate *= 2.0
                if lead <= -2: rate *= 1.3
            elif lead > 0:
                rate *= 0.85
        if minute_real >= 80 and live_duel_left > 0:
            rate *= 1.7
        return min(0.45, rate)

    def _resolve_live_duel(minute: str, minute_real: int, attA: bool) -> bool:
        nonlocal live_duel_left, duels_done, last_duel_minute, score, shots, on_target, xg
        if live_duel_left <= 0: return False
        if last_duel_minute == minute:  # cooldown: nie dwa duelle w dokładnie tej samej minucie
            return False
        idx = 0 if attA else 1
        if rng.random() >= _live_duel_rate(minute_real, idx): return False

        live_duel_left -= 1; duels_done += 1; last_duel_minute = minute

        att, deff = (teamA, teamB) if attA else (teamB, teamA)
        duel_type = rng.choices(["dribble","pass","shoot","penalty"], weights=[0.35,0.25,0.30,0.10])[0]

        if duel_type == "penalty":
            attacker = _pick_attacker(att, rng)
            if attacker.pos == "DEF": attacker = _pick_attacker(att, rng)
            gk = _pick_gk(deff)
            a_act = rng.choice(["penalty_left","penalty_right","penalty_center"])
            d_act = rng.choice(["gk_dive_left","gk_dive_right","gk_stay"])
            header = f"🎮 LIVE DUEL: karny — {attacker.name} vs {gk.name} ({a_act} vs {d_act})"
            log.append(_fmt(minute, att.name, header))
            res = DuelSystem.resolve({"name": attacker.name}, {"name": gk.name}, a_act, d_act, rng=rng)
            # drain za ciężki sprint/nerwy
            _drain(stamA if attA else stamB, [attacker.name], FAT_DUEL_BONUS)
            _drain(stamB if attA else stamA, [gk.name], FAT_DUEL_BONUS*0.7)
        else:
            attacker = _pick_attacker(att, rng)
            defender = _pick_gk(deff) if duel_type == "shoot" and rng.random() < 0.8 else _pick_attacker(deff, rng)
            if duel_type == "dribble":
                a_act = "dribble"; d_act = rng.choices(["press","tackle","block"], weights=[0.4,0.4,0.2])[0]
            elif duel_type == "pass":
                a_act = "pass"; d_act = rng.choices(["press","tackle","block"], weights=[0.35,0.25,0.40])[0]
            else:
                a_act = "shoot"; d_act = rng.choices(["gk_close","gk_stay","gk_block"], weights=[0.5,0.3,0.2])[0]
            header = f"🎮 LIVE DUEL: {attacker.name} vs {defender.name} ({a_act} vs {d_act})"
            log.append(_fmt(minute, att.name, header))
            res = DuelSystem.resolve({"name": attacker.name}, {"name": defender.name}, a_act, d_act, rng=rng)
            # drain dla uczestników
            _drain(stamA if attA else stamB, [attacker.name], FAT_DUEL_BONUS)
            _drain(stamB if attA else stamA, [defender.name], FAT_DUEL_BONUS*0.8)

        for c in res.get("commentary", []):
            log.append(_fmt(minute, att.name, c + " (LIVE DUEL)"))

        oc = res.get("outcome")
        i = 0 if attA else 1
        if oc in ("goal","shot_saved","shot_wide"):
            shots[i] += 1
            _bump(pstatsA if i==0 else pstatsB, attacker.name, "shots", 1)
            xg[i] += float(res.get("xg", 0.0))
        if oc in ("goal","shot_saved"):
            on_target[i] += 1
            _bump(pstatsA if i==0 else pstatsB, attacker.name, "on_target", 1)
            if oc == "shot_saved" and ("gk" in d_act or duel_type=="penalty"):
                # FIX: poprawne zliczanie interwencji GK (karny vs 1v1)
                save_name = None
                if duel_type == "penalty":
                    save_name = gk.name
                elif "gk" in d_act:
                    save_name = defender.name
                if save_name:
                    _bump(pstatsB if i==0 else pstatsA, save_name, "saves", 1)
        if oc == "goal":
            score[i] += 1
            _bump(pstatsA if i==0 else pstatsB, attacker.name, "goals", 1)
            _bump(pstatsA if i==0 else pstatsB, attacker.name, "duel_plus", 1)
            _add_goal_line(minute, att.name, i, sp_tag=" [z LIVE DUEL]", shooter=attacker.name, assister=None)
        elif oc in ("breakthrough","key_pass"):
            _bump(pstatsA if i==0 else pstatsB, attacker.name, "duel_plus", 0.5)
        elif oc in ("intercept","shot_saved"):
            _bump(pstatsB if i==0 else pstatsA, defender.name, "duel_plus", 0.5)
        elif oc in ("lost","shot_wide"):
            _bump(pstatsA if i==0 else pstatsB, attacker.name, "duel_minus", 0.5)
        elif oc == "foul":
            _bump(pstatsB if i==0 else pstatsA, defender.name, "fouls", 1)

        return True

    def sim_half(first_half: bool) -> int:
        add = rng.randint(*STOPPAGE_PER_HALF)
        vmin_total = HALF_VMINUTES + add

        for vm in range(1, vmin_total + 1):
            minute = _minute_label_str(first_half, vm)
            if vm <= HALF_VMINUTES:
                scaled = math.ceil(vm * 45 / HALF_VMINUTES)
                minute_real = scaled if first_half else 45 + max(1, scaled)
            else:
                extra = vm - HALF_VMINUTES
                minute_real = (45 if first_half else 90) + extra

            # bazowy drain stamina (wszyscy) – zależny od stylu
            _drain_base(stamA, teamA.tactic.style, posA)
            _drain_base(stamB, teamB.tactic.style, posB)

            # kontrola gry z poprawką na zmęczenie linii środka
            base_ctrlA = _control_share_eff(teamA, teamB, mod[0], mod[1])
            midA = _avg_stam(stamA, posA, "MID"); midB = _avg_stam(stamB, posB, "MID")
            fA = 0.9 + 0.2*(midA/100.0); fB = 0.9 + 0.2*(midB/100.0)
            adjA = base_ctrlA * fA; adjB = (1.0-base_ctrlA) * fB
            controlA = adjA / max(adjA+adjB, 1e-6)

            for _ in range(MAX_ACTIONS_PER_MIN):
                # posiadanie (tick)
                pos_ticks[0] += controlA
                pos_ticks[1] += (1.0 - controlA)

                # LIVE DUEL
                attA = (rng.random() < controlA)
                if _resolve_live_duel(minute, minute_real, attA):
                    continue

                # standardowa akcja?
                p_action = BASE_ACTION_P
                p_action *= (0.95 + 0.10 * (controlA - 0.5) * 2)
                p_action *= (teamA.tactic.action_rate_mod * controlA + teamB.tactic.action_rate_mod * (1 - controlA))
                p_action = max(0.10, min(0.80, p_action))

                # kto atakuje
                attA = rng.random() < controlA
                att, deff = (teamA, teamB) if attA else (teamB, teamA)
                idx = 0 if attA else 1
                opp = 1 - idx

                # szanse bazowe
                p_sh = _p_shot(att, deff)
                p_gl = _p_goal(att, deff)

                # engagement
                p_action, p_sh, p_gl = _apply_engagement(idx, minute_real, p_action, p_sh, p_gl)
                # fatigue
                p_action, p_sh, p_gl = _apply_fatigue_effects(idx, p_action, p_sh, p_gl)

                # anti-zero
                shots_team = shots[idx]
                if minute_real >= ANTI_ZERO_MINUTE and score[idx] < score[opp] and shots_team == 0 and not anti_zero_used[idx]:
                    p_sh *= ANTI_ZERO_BOOST

                p_sh = max(0.15, min(0.90, p_sh))
                p_gl = max(0.03, min(0.40, p_gl))

                if rng.random() >= p_action:
                    continue

                sp_kind = None

                # FAUL? (rośnie przy niskiej średniej stamina broniących)
                foul_rate_eff = FOUL_RATE
                def_avg = _avg_stam(stamB, posB) if idx == 0 else _avg_stam(stamA, posA)
                if def_avg < FAT_LOW_THRESHOLD:
                    foul_rate_eff *= (1.0 + (FAT_LOW_THRESHOLD - def_avg) / FAT_LOW_THRESHOLD * FAT_LOW_FOUL_BOOST)

                if rng.random() < foul_rate_eff:
                    fouler_idx = opp if rng.random() < FOUL_DEFENDERS_BIAS else idx
                    fouls_t[fouler_idx] += 1
                    foul_team = teamA.name if fouler_idx == 0 else teamB.name

                    pool = (teamB.players if idx==0 else teamA.players) if fouler_idx==opp else (teamA.players if idx==0 else teamB.players)
                    if fouler_idx == opp:  # najczęściej DEF/MID
                        cands = [p for p in pool if p.pos in ("DEF","MID")] or pool
                    else:                  # czasem fauluje atakujący
                        cands = [p for p in pool if p.pos in ("FWD","MID")] or pool
                    fouler = rng.choice(cands)
                    _bump(pstatsA if fouler_idx==0 else pstatsB, fouler.name, "fouls", 1)
                    # zmęczenie też gra rolę – faulujący traci trochę
                    (_drain(stamA, [fouler.name], 1.0) if fouler_idx==0 else _drain(stamB, [fouler.name], 1.0))

                    log.append(_fmt(minute, foul_team, "✋ Faul"))

                    r = rng.random()
                    if r < RED_PROB:
                        rc_t[fouler_idx] += 1; mod[fouler_idx] *= RED_MOD
                        _bump(pstatsA if fouler_idx==0 else pstatsB, fouler.name, "rc", 1)
                        log.append(_fmt(minute, foul_team, "🟥 Czerwona kartka!"))
                    elif r < RED_PROB + YELLOW_PROB:
                        yc_t[fouler_idx] += 1
                        _bump(pstatsA if fouler_idx==0 else pstatsB, fouler.name, "yc", 1)
                        log.append(_fmt(minute, foul_team, "🟨 Żółta kartka"))

                    sp_kind = "freekick"
                    if fouler_idx == idx:
                        # po faulu atakującego – piłka dla przeciwnika
                        att, deff = deff, att
                        idx, opp = opp, idx
                    log.append(_fmt(minute, att.name, "🎯 Rzut wolny"))

                # SFG / zapowiedź
                if sp_kind is None:
                    if rng.random() < SET_PIECE_RATE:
                        sp_kind = "corner" if rng.random() < CORNER_SHARE else "freekick"
                        log.append(_fmt(minute, att.name, "🏳️ Rzut rożny")) if sp_kind == "corner" else log.append(_fmt(minute, att.name, "🎯 Rzut wolny"))
                    else:
                        ann = comments.pick("announce", team=att.name, minute=minute)
                        log.append(_fmt(minute, att.name, ann))

                # Rezultat
                if rng.random() < p_sh:
                    shots[idx] += 1
                    if minute_real >= ANTI_ZERO_MINUTE and shots[idx] == 1: anti_zero_used[idx] = True
                    shooter = rng.choice(att.players) if att.players else _pick_attacker(att, rng)
                    if shooter.pos == "GK": shooter = _pick_attacker(att, rng)
                    _bump(pstatsA if idx==0 else pstatsB, shooter.name, "shots", 1)

                    # koszt zmęczenia za udział w akcji
                    (_drain(stamA, [shooter.name], FAT_EVENT_BONUS) if idx==0 else _drain(stamB, [shooter.name], FAT_EVENT_BONUS))

                    # xG dla strzału (SFG lekki bonus)
                    shot_xg = p_gl * (1.10 if sp_kind == "freekick" else (1.05 if sp_kind == "corner" else 1.00))
                    xg[idx] += float(max(0.01, min(0.95, shot_xg)))

                    if rng.random() < p_gl:
                        score[idx] += 1; on_target[idx] += 1
                        _bump(pstatsA if idx==0 else pstatsB, shooter.name, "on_target", 1)
                        _bump(pstatsA if idx==0 else pstatsB, shooter.name, "goals", 1)
                        assister = None
                        if rng.random() < 0.70:
                            assister = _pick_assister(att, shooter, rng)
                            if assister:
                                _bump(pstatsA if idx==0 else pstatsB, assister.name, "assists", 1)
                                # asystent też się zmęczył
                                (_drain(stamA, [assister.name], FAT_EVENT_BONUS*0.6) if idx==0 else _drain(stamB, [assister.name], FAT_EVENT_BONUS*0.6))
                        tag = "po rzucie rożnym" if sp_kind == "corner" else ("po rzucie wolnym" if sp_kind == "freekick" else "z akcji")
                        _add_goal_line(minute, att.name, idx, sp_tag=f"  ({tag})", shooter=shooter.name, assister=(assister.name if assister else None))
                    else:
                        if rng.random() < 0.6:
                            on_target[idx] += 1
                            _bump(pstatsA if idx==0 else pstatsB, shooter.name, "on_target", 1)
                            gk = _pick_gk(deff)
                            _bump(pstatsB if idx==0 else pstatsA, gk.name, "saves", 1)
                            # GK też pracuje
                            (_drain(stamB, [gk.name], FAT_EVENT_BONUS*0.5) if idx==0 else _drain(stamA, [gk.name], FAT_EVENT_BONUS*0.5))
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
                        if which < 0.4: rtxt = comments.pick("throw_in", team=att.name, minute=minute)
                        elif which < 0.8: rtxt = comments.pick("clearance", team=att.name, minute=minute)
                        else: rtxt = comments.pick("corner_wasted", team=att.name, minute=minute)
                        log.append(_fmt(minute, att.name, rtxt))

            if rng.random() < LIVE_RATE:
                msg = livepack.maybe()
                if msg: log.append(f"{minute} 🟢 LIVE: {msg}")

        return add

    add1 = sim_half(first_half=True)
    avgA_ht = round(_avg_stam(stamA, posA))
    avgB_ht = round(_avg_stam(stamB, posB))
    log.append(f"HT • Przerwa ({score[0]}:{score[1]}). Doliczono +{add1}'.")
    log.append(f"🔋 Śr. stamina do przerwy: {teamA.name} {avgA_ht}% – {teamB.name} {avgB_ht}%")

    add2 = sim_half(first_half=False)
    log.append(f"FT • Koniec ({score[0]}:{score[1]}). Doliczono +{add2}'.")

    # Posiadanie %
    total_ticks = max(1e-6, pos_ticks[0] + pos_ticks[1])
    posA_share = int(round(100.0 * pos_ticks[0] / total_ticks))
    posB_share = 100 - posA_share

    # xG podsumowanie
    xgA, xgB = round(xg[0], 2), round(xg[1], 2)
    log.append(f"📊 xG: {teamA.name} {xgA:.2f} – {teamB.name} {xgB:.2f}")
    log.append(f"🔁 Posiadanie: {teamA.name} {posA_share}% – {teamB.name} {posB_share}%")

    # stamina końcowa (debug/immersja)
    avgA_ft = round(_avg_stam(stamA, posA))
    avgB_ft = round(_avg_stam(stamB, posB))
    log.append(f"🔋 Śr. stamina koniec: {teamA.name} {avgA_ft}% – {teamB.name} {avgB_ft}%")

    # Oceny
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
        "xg": {"A": xgA, "B": xgB},
        "possession": {"A": posA_share, "B": posB_share},
        "seed": seed,
    }
