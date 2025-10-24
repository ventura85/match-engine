using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

namespace MatchEngine.Tests.Engine;

public class CommentaryProbabilitySmokeTests
{
    [Fact]
    public void Minor_events_have_nonzero_and_reasonable_rates()
    {
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        var counts = new Dictionary<EventType,(int with,int total)>
        {
            [EventType.BuildUp] = (0,0),
            [EventType.FinalThird] = (0,0),
            [EventType.DuelWon] = (0,0),
            [EventType.DuelLost] = (0,0),
        };

        for (int s = 0; s < 50; s++)
        {
            var r = new EngineMatch(a, b, 1000 + s).Simulate(90);
            foreach (var e in r.EventsFull)
            {
                if (!counts.ContainsKey(e.Type)) continue;
                var c = counts[e.Type];
                c.total++;
                if (!string.IsNullOrWhiteSpace(e.Description)) c.with++;
                counts[e.Type] = c;
            }
        }

        // sanity bands (broad)
        var build = counts[EventType.BuildUp];
        build.total.Should().BeGreaterThan(0);
        Fraction(build).Should().BeInRange(0.05, 0.45);

        var f3 = counts[EventType.FinalThird];
        f3.total.Should().BeGreaterThan(0);
        Fraction(f3).Should().BeInRange(0.10, 0.55);

        var dw = counts[EventType.DuelWon];
        dw.total.Should().BeGreaterThan(0);
        Fraction(dw).Should().BeInRange(0.05, 0.45);

        var dl = counts[EventType.DuelLost];
        dl.total.Should().BeGreaterThan(0);
        Fraction(dl).Should().BeInRange(0.05, 0.45);
    }

    private static double Fraction((int with, int total) t)
        => t.total == 0 ? 0 : t.with / (double)t.total;
}

