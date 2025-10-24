using System.Linq;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using MatchEngineType = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

public class DuelsCountersTests
{
    [Fact]
    public void DuelsCountersNonNegativeAndConsistent()
    {
        var r = new MatchEngineType(SeedData.Red_433_Attacking(), SeedData.Blue_4141_Balanced(), 2025).Simulate(90);
        Assert.True(r.Stats.DuelsTotalA >= r.Stats.DuelsWonA);
        Assert.True(r.Stats.DuelsTotalB >= r.Stats.DuelsWonB);
        int wonA = r.EventsFull.Count(e => e.Type == EventType.DuelWon && e.Team == r.TeamA);
        int lostA = r.EventsFull.Count(e => e.Type == EventType.DuelLost && e.Team == r.TeamA);
        int wonB = r.EventsFull.Count(e => e.Type == EventType.DuelWon && e.Team == r.TeamB);
        int lostB = r.EventsFull.Count(e => e.Type == EventType.DuelLost && e.Team == r.TeamB);
        Assert.Equal(wonA + lostA, r.Stats.DuelsTotalA);
        Assert.Equal(wonB + lostB, r.Stats.DuelsTotalB);
        Assert.Equal(wonA, r.Stats.DuelsWonA);
        Assert.Equal(wonB, r.Stats.DuelsWonB);
    }
}

