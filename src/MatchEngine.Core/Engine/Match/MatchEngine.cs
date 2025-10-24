using System.Collections.Generic;
using MatchEngine.Core.Domain.Teams;
using MatchEngine.Core.Engine.Events;
using MatchEngine.Core.Engine.RNG;
using EngineStats = MatchEngine.Core.Engine.Stats.Stats;
using MatchEngine.Core.Reporting;
using MatchEngine.Core.Engine.Commentary;

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

        // commentary pass: fill descriptions deterministically using "commentary" stream
        ApplyCommentary(full, key);

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

    private void ApplyCommentary(List<Event> full, List<Event> key)
    {
        var repo = TryCreateDefaultRepo();
        if (repo == null) return;
        var composer = new CommentaryComposer(_rng.Get("commentary"), repo, locale: "pl", tone: "fun", cooldownSize: 6, policy: new CommentaryPolicy());

        // map and replace events with descriptions
        for (int i = 0; i < full.Count; i++)
        {
            var e = full[i];
            if (IsKeyForCommentary(e.Type))
            {
                var name = EventCatalog.GetName((int)e.Type);
                var team = e.Team;
                var opp = team == _a.Name ? _b.Name : team == _b.Name ? _a.Name : string.Empty;
                var line = composer.Compose(name, e.Minute, team, opp);
                if (!string.IsNullOrWhiteSpace(line))
                {
                    full[i] = new Event(e.Minute, e.Type, e.Team, line);
                }
            }
            else
            {
                var name = EventCatalog.GetName((int)e.Type);
                var team = e.Team;
                var opp = team == _a.Name ? _b.Name : team == _b.Name ? _a.Name : string.Empty;
                var micro = composer.TryComposeMicro(name, e.Minute, team, opp, i);
                if (!string.IsNullOrWhiteSpace(micro))
                {
                    full[i] = new Event(e.Minute, e.Type, e.Team, micro);
                }
            }
        }

        // re-emit for key list as well
        for (int i = 0; i < key.Count; i++)
        {
            var e = key[i];
            if (IsKeyForCommentary(e.Type))
            {
                var name = EventCatalog.GetName((int)e.Type);
                var team = e.Team;
                var opp = team == _a.Name ? _b.Name : team == _b.Name ? _a.Name : string.Empty;
                var line = composer.Compose(name, e.Minute, team, opp);
                if (!string.IsNullOrWhiteSpace(line))
                {
                    key[i] = new Event(e.Minute, e.Type, e.Team, line);
                }
            }
        }
    }

    private static bool IsKeyForCommentary(EventType t)
        => t == EventType.Goal
        || t == EventType.SaveMade
        || t == EventType.ShotOnTarget
        || t == EventType.FreekickAwarded
        || t == EventType.CornerAwarded
        || t == EventType.FoulCommitted
        || t == EventType.YellowCard
        || t == EventType.RedCard
        || t == EventType.PenaltyAwarded
        || t == EventType.FinalWhistle
        || t == EventType.Kickoff;

    // no mapping needed; using enum string names directly

    private static ICommentRepository? TryCreateDefaultRepo()
    {
        try
        {
            // Default location relative to app root or working directory
            return new JsonCommentRepository("assets/comments");
        }
        catch
        {
            return null;
        }
    }
}
