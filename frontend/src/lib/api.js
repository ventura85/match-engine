const API = import.meta.env.VITE_API_URL;

export async function fetchTeams() {
  const r = await fetch(`${API}/teams`);
  if (!r.ok) throw new Error('Teams fetch failed');
  return r.json();
}

export async function simulate(seed, teamA, teamB) {
  const r = await fetch(`${API}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seed, teamA, teamB }),
  });
  if (!r.ok) throw new Error('Simulate failed');
  return r.json();
}

