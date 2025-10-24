import { useEffect, useMemo, useState } from 'react';
import { fetchTeams, simulate } from './lib/api';
import './App.css';

const ICON = {
  Goal: '⚽',
  ShotOnTarget: '🎯',
  Shot: '💥',
  CornerAwarded: '⛳',
  FreekickAwarded: '🟨',
  PenaltyAwarded: '⚠️',
  YellowCard: '🟨',
  RedCard: '🟥',
  SaveMade: '🧤',
  DuelWon: '🟢',
  DuelLost: '🔴',
  FinalWhistle: '⏱️',
};

export default function App() {
  const [teams, setTeams] = useState([]);
  const [teamA, setTeamA] = useState('Red');
  const [teamB, setTeamB] = useState('Blue');
  const [seed, setSeed] = useState(42);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    fetchTeams().then(setTeams).catch(e => setErr(String(e)));
  }, []);

  const possA = report ? Number(report.stats.possessionA?.toFixed(1)) : 0;
  const possB = report ? Number(report.stats.possessionB?.toFixed(1)) : 0;

  const rows = useMemo(() => {
    if (!report) return [];
    const s = report.stats;
    return [
      ['Posiadanie %', `${possA}%`, `${possB}%`],
      ['Strzały (celne)', `${s.shotsA} (${s.shotsOnTargetA})`, `${s.shotsB} (${s.shotsOnTargetB})`],
      ['xG', s.xgA?.toFixed(2), s.xgB?.toFixed(2)],
      ['Rogi', s.cornersA, s.cornersB],
      ['Wolne', s.freekicksA, s.freekicksB],
      ['Karne', s.penaltiesA, s.penaltiesB],
      ['Faule', s.foulsA, s.foulsB],
      ['Żółte', s.yellowsA, s.yellowsB],
      ['Czerwone', s.redsA, s.redsB],
      ['Pojedynki (wygrane/łącznie)', `${s.duelsWonA ?? 0}/${s.duelsTotalA ?? 0}`, `${s.duelsWonB ?? 0}/${s.duelsTotalB ?? 0}`],
    ];
  }, [report, possA, possB]);

  async function run() {
    setLoading(true); setErr(null);
    try { setReport(await simulate(seed, teamA, teamB)); }
    catch (e) { setErr(String(e)); }
    finally { setLoading(false); }
  }

  return (
    <div className="container">
      <h1>⚽ Match Engine – MVP</h1>

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
      </div>

      {err && <div className="error">Błąd: {err}</div>}
      {loading && <div>Symulacja…</div>}

      {report && (
        <div className="grid">
          <div className="card">
            <h3>Wynik</h3>
            <div className="score">
              {report.teamA} {report.scoreA} – {report.scoreB} {report.teamB}
            </div>
            <div className="sub">schema v{report.schemaVersion}</div>
            <div style={{marginTop:12}}>
              <div className="poss-bar" title={`Posiadanie: ${possA}% / ${possB}%`}>
                <span className="poss-a" style={{width: `${possA}%`}} />
                <span className="poss-b" style={{width: `${possB}%`}} />
              </div>
              <div className="sub" style={{display:'flex', justifyContent:'space-between', marginTop:6}}>
                <span>{report.teamA} {possA}%</span>
                <span>{report.teamB} {possB}%</span>
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
            <h3>Chronologia (skrót)</h3>
            <div className="events">
              {report.events.map((e, i) => (
                <div key={i} className="event">
                  <div className="min">{e.minute}'</div>
                  <div>
                    <span className="badge" style={{marginRight:8}}>
                      {ICON[e.type] ?? '•'} {e.type}
                    </span>
                    <strong>{e.team}</strong>
                    {e.description ? ` — ${e.description}` : ''}
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

