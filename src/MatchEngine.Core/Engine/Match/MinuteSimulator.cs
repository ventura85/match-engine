using MatchEngine.Core.Engine.Events;
using MatchEngine.Core.Engine.RNG;
using EngineStats = MatchEngine.Core.Engine.Stats.Stats;
using MatchEngine.Core.Engine.Xg;

namespace MatchEngine.Core.Engine.Match;

public static class MinuteSimulator
{
    public static void Step(MatchState s, EngineStats st, List<Event> key, List<Event> full)
    {
        var rngPoss = s.Rng.Get("possession");
        var rngPhase = s.Rng.Get("phases");
        var rngShot = s.Rng.Get("shots");
        var rngSp = s.Rng.Get("setpieces");
        var rngCards = s.Rng.Get("cards");

        // 1) Possession tilt from tactics (simple MVP)
        double tilt = 0.5;
        tilt += Tilt(s.A.Tactics) * 0.04;
        tilt -= Tilt(s.B.Tactics) * 0.04;
        tilt = Math.Clamp(tilt, 0.30, 0.70);
        bool aHasBall = rngPoss.NextDouble() < tilt;
        if (aHasBall) s.PossA++; else s.PossB++;

        var teamName = aHasBall ? s.A.Name : s.B.Name;
        full.Add(new Event(s.Minute, EventType.BuildUp, teamName));

        // 2) Phase: chance to reach final third & attempt shot
        bool finalThird = rngPhase.NextDouble() < 0.55;
        if (!finalThird) return;
        full.Add(new Event(s.Minute, EventType.FinalThird, teamName));

        // 3) Sometimes set-piece instead of open play
        if (rngSp.NextDouble() < 0.07)
        {
            full.Add(new Event(s.Minute, EventType.FreekickAwarded, teamName));
            if (aHasBall) st.FreekicksA++; else st.FreekicksB++;
            // tiny chance direct shot from FK
            if (rngShot.NextDouble() < 0.30) ResolveShot(s, st, key, full, aHasBall, setPiece: true);
            return;
        }
        if (rngSp.NextDouble() < 0.08)
        {
            full.Add(new Event(s.Minute, EventType.CornerAwarded, teamName));
            if (aHasBall) st.CornersA++; else st.CornersB++;
            // quick corner shot chance
            if (rngShot.NextDouble() < 0.35) ResolveShot(s, st, key, full, aHasBall, setPiece: true);
            return;
        }

        // 4) Open play shot?
        if (rngShot.NextDouble() < 0.42) ResolveShot(s, st, key, full, aHasBall, setPiece: false);

        // 5) Foul/cards (neutral ref mvp)
        if (rngCards.NextDouble() < 0.06)
        {
            var foulTeam = aHasBall ? s.B.Name : s.A.Name; // defending team fouls
            full.Add(new Event(s.Minute, EventType.FoulCommitted, foulTeam));
            if (rngCards.NextDouble() < 0.25)
            {
                full.Add(new Event(s.Minute, EventType.YellowCard, foulTeam));
                if (foulTeam == s.A.Name) st.YellowsA++; else st.YellowsB++;
            }
        }
    }

    static void ResolveShot(MatchState s, EngineStats st, List<Event> key, List<Event> full, bool aHasBall, bool setPiece)
    {
        if (aHasBall) st.ShotsA++; else st.ShotsB++;
        var atkTeam = aHasBall ? s.A.Name : s.B.Name;
        full.Add(new Event(s.Minute, EventType.Shot, atkTeam));
        // on-target chance
        var onTarget = s.Rng.Get("shots").NextDouble() < (setPiece ? 0.55 : 0.48);
        if (onTarget)
        {
            if (aHasBall) st.ShotsOnTargetA++; else st.ShotsOnTargetB++;
            full.Add(new Event(s.Minute, EventType.ShotOnTarget, atkTeam));
            // xG & goal
            var xg = XgModel.ShotXg(distanceM: 12 + s.Rng.Get("shots").Next(0, 13), angleDeg: 20 + s.Rng.Get("shots").Next(0, 61), setPiece);
            if (aHasBall) st.XgA += xg; else st.XgB += xg;
            var goal = s.Rng.Get("shots").NextDouble() < Math.Clamp(xg * 0.9, 0.05, 0.7);
            if (goal)
            {
                if (aHasBall) st.GoalsA++; else st.GoalsB++;
                full.Add(new Event(s.Minute, EventType.Goal, atkTeam));
                key.Add(new Event(s.Minute, EventType.Goal, atkTeam));
            }
        }
    }

    static double Tilt(Domain.Teams.Tactics t)
        => t.Style switch
        {
            Domain.Teams.Style.Attacking => +1,
            Domain.Teams.Style.Defensive => -1,
            _ => 0
        } + (t.Pressing == Domain.Teams.Pressing.High ? +0.5 : t.Pressing == Domain.Teams.Pressing.Low ? -0.5 : 0);
}
