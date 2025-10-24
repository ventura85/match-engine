using System.Linq;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using MatchEngineType = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

namespace MatchEngine.Tests.Engine;

public class M3FoulsTests
{
    [Fact]
    public void Fouls_count_matches_events_single_seed()
    {
        var a = SeedData.Red_433_Attacking();
        var b = SeedData.Blue_4141_Balanced();
        var r = new MatchEngineType(a, b, 42).Simulate(90);

        int foulsA = r.EventsFull.Count(e => e.Type == EventType.FoulCommitted && e.Team == r.TeamA);
        int foulsB = r.EventsFull.Count(e => e.Type == EventType.FoulCommitted && e.Team == r.TeamB);

        Assert.Equal(foulsA, r.Stats.FoulsA);
        Assert.Equal(foulsB, r.Stats.FoulsB);
    }

    [Fact]
    public void Fouls_count_matches_events_multi_seed()
    {
        var a = SeedData.Red_433_Attacking();
        var b = SeedData.Blue_4141_Balanced();
        for (int seed = 1; seed <= 10; seed++)
        {
            var r = new MatchEngineType(a, b, seed * 123).Simulate(90);
            int foulsA = r.EventsFull.Count(e => e.Type == EventType.FoulCommitted && e.Team == r.TeamA);
            int foulsB = r.EventsFull.Count(e => e.Type == EventType.FoulCommitted && e.Team == r.TeamB);
            Assert.Equal(foulsA, r.Stats.FoulsA);
            Assert.Equal(foulsB, r.Stats.FoulsB);
        }
    }
}

