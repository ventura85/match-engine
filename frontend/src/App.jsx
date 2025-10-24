import React, { useEffect, useMemo, useState } from 'react';
import { fetchTeams, simulate } from './lib/api';
import './App.css';

const ICON = {
  Goal: 'âš˝',
  ShotOnTarget: 'đźŽŻ',
  Shot: 'đź’Ą',
  CornerAwarded: 'â›ł',
  FreekickAwarded: 'đź§±',
  PenaltyAwarded: 'âš ď¸Ź',
  YellowCard: 'đźź¨',
  RedCard: 'đźźĄ',
  SaveMade: 'đź§¤',
  DuelWon: 'đźź˘',
  DuelLost: 'đź”´',
  FinalWhistle: 'âŹ±ď¸Ź',
};
const LABELS = {
  Goal: 'Gol',
  ShotOnTarget: 'StrzaĹ‚ celny',
  Shot: 'StrzaĹ‚',
  CornerAwarded: 'Rzut roĹĽny',
  FreekickAwarded: 'Rzut wolny',
  PenaltyAwarded: 'Rzut karny',
  YellowCard: 'Ĺ»ĂłĹ‚ta kartka',
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

export default function App() {
  const [teams, setTeams] = useState([]);
  const [teamA, setTeamA] = useState('Red');
  const [teamB, setTeamB] = useState('Blue');
  const [seed, setSeed] = useState(42);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [mode, setMode] = useState('key'); // 'key' | 'full'

  useEffect(() => {
    fetchTeams().then(setTeams).catch(e => setErr(String(e)));
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
      ['Posiadanie %', pct(report.stats.possessionA), pct(report.stats.possessionB)],
      ['StrzaĹ‚y (celne)', `${s.shotsA} (${s.shotsOnTargetA})`, `${s.shotsB} (${s.shotsOnTargetB})`],
      ['xG', nf2.format(s.xgA ?? 0), nf2.format(s.xgB ?? 0)],
      ['Rogi', s.cornersA, s.cornersB],
      ['Wolne', s.freekicksA, s.freekicksB],
      ['Karne', s.penaltiesA, s.penaltiesB],
      ['Faule', s.foulsA ?? 0, s.foulsB ?? 0],
      ['Ĺ»ĂłĹ‚te', s.yellowsA ?? 0, s.yellowsB ?? 0],
      ['Czerwone', s.redsA ?? 0, s.redsB ?? 0],
      ['Pojedynki (wygrane/Ĺ‚Ä…cznie)', `${s.duelsWonA ?? 0}/${s.duelsTotalA ?? 0}`, `${s.duelsWonB ?? 0}/${s.duelsTotalB ?? 0}`],
    ];
  }, [report]);

  async function run() {
    setLoading(true); setErr(null);
    try { setReport(await simulate(seed, teamA, teamB)); }
    catch (e) { setErr(String(e)); }
    finally { setLoading(false); }
  }

  return (
    <div className="container">
      <h1>âš˝ Match Engine â€“ MVP</h1>

      <div className="toolbar">
        <label>Team A:{' '}
          <select value={teamA} onChange={e=>setTeamA(e.target.value)}>
            {teams.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label>Team B:{' '}
          <select value={teamB} onChange={e=>setTeamB(e.target.value)}>
            {teams.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label>Seed:{' '}
          <input type="number" value={seed} onChange={e=>setSeed(Number(e.target.value))} style={{width:90}}/>
        </label>
        <button onClick={run} disabled={loading}>Start</button>
        <div className="seg">
          <button className={mode==='key'?'on':''} onClick={()=>setMode('key')}>SkrĂłt</button>
          <button className={mode==='full'?'on':''} onClick={()=>setMode('full')}>PeĹ‚na</button>
        </div>
      </div>

      {err && <div className="error">BĹ‚Ä…d: {err}</div>}
      {loading && <div>Symulacjaâ€¦</div>}

      {report && (
        <div className="grid">
          <div className="card">
            <h3>Wynik</h3>
            <div className="score">
              {report.teamA} {report.scoreA} â€“ {report.scoreB} {report.teamB}
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
            <h3>Chronologia (skrĂłt)</h3>
            <div className="events">
              {evs.map((e, i) => (
                <div key={i} className="event">
                  <div className="min">{e.minute}'</div>
                  <div>
                    <span className="badge" style={{marginRight:8}}>
                      {ICON[e.type] ?? 'â€˘'} {LABELS[e.type] ?? e.type}
                    </span>{' '}
                    <strong>{e.team}</strong>
                    {e.description ? ` â€” ${e.description}` : ''}
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
