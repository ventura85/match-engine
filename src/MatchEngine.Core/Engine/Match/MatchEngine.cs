using System.Collections.Generic;
using MatchEngine.Core.Domain.Teams;
using MatchEngine.Core.Engine.Events;
using MatchEngine.Core.Engine.RNG;
using EngineStats = MatchEngine.Core.Engine.Stats.Stats;
using MatchEngine.Core.Reporting;

namespace MatchEngine.Core.Engine.Match;

public sealed class MatchEngine
{
    readonly Team _a, _b;
    RngRegistry _rng;

    public MatchEngine(Team a, Team b, int seed)
    {
        _a = a;
        _b = b;
        _rng = new RngRegistry(seed);
    }

    public MatchReport Simulate(int minutes = 90)
    {
        var st = new EngineStats();
        var full = new List<Event>();
        var key = new List<Event>();
        var state = new MatchState(_a, _b, _rng);

        full.Add(new Event(0, EventType.Kickoff, _a.Name));
        for (state.Minute = 1; state.Minute <= minutes; state.Minute++)
            MinuteSimulator.Step(state, st, key, full);
        full.Add(new Event(minutes, EventType.FinalWhistle, "referee"));

        // possession %
        var totalPoss = Math.Max(1, state.PossA + state.PossB);
        st.PossessionA = 100.0 * state.PossA / totalPoss;
        st.PossessionB = 100.0 * state.PossB / totalPoss;

        var report = new MatchReport
        {
            TeamA = _a.Name,
            TeamB = _b.Name,
            ScoreA = st.GoalsA,
            ScoreB = st.GoalsB,
            Stats = st,
            EventsNdjson = Reporting.NdjsonWriter.Write(full)
        };
        report.Events.AddRange(key);
        report.EventsFull.AddRange(full);
        return report;
    }
}
