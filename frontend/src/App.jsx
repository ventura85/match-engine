import React, { useEffect, useMemo, useState } from 'react';
import { fetchTeams, simulate } from './lib/api';
import './App.css';

// Icons (Unicode escapes to avoid encoding issues)
const ICON = {
  Goal: '\u26BD',                // ⚽
  ShotOnTarget: '\uD83C\uDFAF', // 🎯
  Shot: '\uD83D\uDCA5',         // 💥
  CornerAwarded: '\u26F3',       // ⛳
  FreekickAwarded: '\uD83E\uDDF1', // 🧱
  PenaltyAwarded: '\u26A0\uFE0F',  // ⚠️
  YellowCard: '\uD83D\uDFE8',   // 🟨
  RedCard: '\uD83D\uDFE5',      // 🟥
  SaveMade: '\uD83E\uDDE4',     // 🧤
  DuelWon: '\uD83D\uDFE2',      // 🟢
  DuelLost: '\uD83D\uDD34',     // 🔴
  FinalWhistle: '\u23F1\uFE0F', // ⏱️
};

// Polish labels (escaped diacritics to avoid encoding problems)
const LABELS = {
  Goal: 'Gol',
  ShotOnTarget: 'Strza\u0142 celny',
  Shot: 'Strza\u0142',
  CornerAwarded: 'Rzut ro\u017Cny',
  FreekickAwarded: 'Rzut wolny',
  PenaltyAwarded: 'Rzut karny',
  YellowCard: '\u017B\u00F3\u0142ta kartka',
  RedCard: 'Czerwona kartka',
  SaveMade: 'Interwencja GK',
  DuelWon: 'Wygrany pojedynek',
  DuelLost: 'Przegrany pojedynek',
  FinalWhistle: 'Koniec meczu',
};

const nf = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 2 });
const pct = v => `${nf.format(v)}%`;
const clamp01 = v => Math.max(0, Math.min(100, v));

// Helpers: NDJSON/Download/Fingerprint
function toNdjson(report) {
  const events = (report?.eventsFull ?? []).map(e => JSON.stringify(e));
  return events.join('\n');
}

function download(filename, text) {
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function fingerprint(report) {
  const evs = report?.events ?? [];
  const basis = evs.map(e => `${e.minute}|${e.type}|${e.team}`).join('\n');
  const enc = new TextEncoder();
  const data = enc.encode(basis);
  const hash = await crypto.subtle.digest('SHA-256', data);
  const bytes = new Uint8Array(hash);
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

export default function App() {
  const [teams, setTeams] = useState([]);
  const [teamA, setTeamA] = useState(''); // preset id
  const [teamB, setTeamB] = useState(''); // preset id
  const [seed, setSeed] = useState(42);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [mode, setMode] = useState('key'); // 'key' | 'full'

  useEffect(() => {
    fetchTeams()
      .then(data => {
        const arr = Array.isArray(data) ? data : [];
        setTeams(arr);
        if (arr.length > 0) {
          setTeamA(arr[0].id);
          setTeamB((arr[1]?.id) ?? arr[0].id);
        }
      })
      .catch(e => setErr(String(e)));
  }, []);

  const possA = report ? (report.stats?.possessionA ?? 0) : 0;
  const possB = report ? (report.stats?.possessionB ?? 0) : 0;

  const evs = report
    ? (mode === 'key'
        ? (report.events?.length ? report.events : report.eventsFull)
        : report.eventsFull)
    : [];

  const rows = useMemo(() => {
    if (!report) return [];
    const s = report.stats;
    return [
      ['Posiadanie %', pct(s.possessionA ?? 0), pct(s.possessionB ?? 0)],
      ['Strza\u0142y (celne)', `${s.shotsA} (${s.shotsOnTargetA})`, `${s.shotsB} (${s.shotsOnTargetB})`],
      ['xG', nf2.format(s.xgA ?? 0), nf2.format(s.xgB ?? 0)],
      ['Rogi', s.cornersA, s.cornersB],
      ['Wolne', s.freekicksA, s.freekicksB],
      ['Karne', s.penaltiesA, s.penaltiesB],
      ['Faule', s.foulsA ?? 0, s.foulsB ?? 0],
      ['\u017B\u00F3\u0142te', s.yellowsA ?? 0, s.yellowsB ?? 0],
      ['Czerwone', s.redsA ?? 0, s.redsB ?? 0],
      ['Pojedynki (wygrane/\u0142\u0105cznie)', `${s.duelsWonA ?? 0}/${s.duelsTotalA ?? 0}`, `${s.duelsWonB ?? 0}/${s.duelsTotalB ?? 0}`],
    ];
  }, [report]);

  async function run() {
    setLoading(true); setErr(null);
    try { setReport(await simulate(Number(seed) || 42, teamA, teamB)); }
    catch (e) { setErr(String(e)); }
    finally { setLoading(false); }
  }

  return (
    <div className="container">
      <h1>{'\u26BD'} Match Engine {'\u2013'} MVP</h1>

      <div className="toolbar">
        <label>Team A{' '}
          <select value={teamA} onChange={e=>setTeamA(e.target.value)}>
            {teams.map(t => (
              <option key={t.id || t.name} value={t.id}>
                {t.name} {'\u2014'} {t.formation} {'\u00B7'} {t.style}
              </option>
            ))}
          </select>
        </label>
        <label>Team B{' '}
          <select value={teamB} onChange={e=>setTeamB(e.target.value)}>
            {teams.map(t => (
              <option key={t.id || t.name} value={t.id}>
                {t.name} {'\u2014'} {t.formation} {'\u00B7'} {t.style}
              </option>
            ))}
          </select>
        </label>
        <label>Seed{' '} 
          <input type="number" value={seed} onChange={e=>setSeed(Number(e.target.value))} style={{width:90}}/>
        </label>
        <button onClick={run} disabled={loading}>Start</button>
        <div className="seg">
          <button className={mode==='key'?'on':''} onClick={()=>setMode('key')}>Skr{`\u00F3`}t</button>
          <button className={mode==='full'?'on':''} onClick={()=>setMode('full')}>Pe{`\u0142`}na</button>
        </div>
        {report && (
          <div className="export">
            <button onClick={() => navigator.clipboard.writeText(JSON.stringify(report)).catch(()=>{})}>
              Kopiuj JSON
            </button>
            <button onClick={() => {
              const sanitize = s => String(s ?? '').replace(/[^a-z0-9-_]+/gi, '_');
              const fn = `report_${sanitize(report.teamA)}_vs_${sanitize(report.teamB)}_seed${String(seed)}.json`;
              download(fn, JSON.stringify(report));
            }}>
              Pobierz JSON
            </button>
            <button onClick={() => {
              const sanitize = s => String(s ?? '').replace(/[^a-z0-9-_]+/gi, '_');
              const fn = `report_${sanitize(report.teamA)}_vs_${sanitize(report.teamB)}_seed${String(seed)}.ndjson`;
              download(fn, toNdjson(report));
            }}>
              Pobierz NDJSON
            </button>
            <button onClick={async () => {
              try {
                const fp = await fingerprint(report);
                await navigator.clipboard.writeText(fp);
              } catch { /* noop */ }
            }}>
              Kopiuj fingerprint
            </button>
          </div>
        )}
      </div>

      {err && <div className="error">B{`\u0142`}{`\u0105`}d: {err}</div>}
      {loading && <div>Symulacja{`\u2026`}</div>}

      {report && (
        <div className="grid">
          <div className="card">
            <h3>Wynik</h3>
            <div className="score">
              {report.teamA} {report.scoreA} - {report.scoreB} {report.teamB}
            </div>
            <div className="sub">schema v{report.schemaVersion}</div>
            <div style={{marginTop:12}}>
              <div className="poss-bar" title={`Posiadanie: ${possA}% / ${possB}%`}>
                <span className="poss-a" style={{width: `${clamp01(possA)}%`}} />
                <span className="poss-b" style={{width: `${clamp01(possB)}%`}} />
              </div>
              <div className="sub" style={{display:'flex', justifyContent:'space-between', marginTop:6}}>
                <span>{report.teamA} {pct(report.stats?.possessionA ?? 0)}</span>
                <span>{report.teamB} {pct(report.stats?.possessionB ?? 0)}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3>Statystyki</h3>
            <table className="table">
              <thead>
                <tr><th>Metryka</th><th>{report.teamA}</th><th>{report.teamB}</th></tr>
              </thead>
              <tbody>
                {rows.map(([k,a,b]) => (
                  <tr key={k}><td>{k}</td><td>{a}</td><td>{b}</td></tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card" style={{gridColumn: '1 / -1'}}>
            <h3>Chronologia (skr{`\u00F3`}t)</h3>
            <div className="events">
              {evs.map((e, i) => (
                <div key={`${e.minute}-${e.type}-${e.team}-${i}`} className="event" title={e.description || undefined}>
                  <div className="min">{e.minute}'</div>
                  <div>
                    <span className="badge" style={{marginRight:8}}>
                      {ICON[e.type] ?? '*'} {LABELS[e.type] ?? e.type}
                    </span>{' '}
                    <strong>{e.team}</strong>
                    {e.description ? <span className="desc"> {'\u2014'} {e.description}</span> : ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
