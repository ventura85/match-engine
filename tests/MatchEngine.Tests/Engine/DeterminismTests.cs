using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngineType = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

public class DeterminismTests
{
    [Fact]
    public void SameSeedSameReport()
    {
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        var r1 = new MatchEngineType(a, b, 123).Simulate(90);
        var r2 = new MatchEngineType(SeedData.Red_433_Attacking(), SeedData.Blue_4141_Balanced(), 123).Simulate(90);
        Assert.Equal(r1.ScoreA, r2.ScoreA);
        Assert.Equal(r1.ScoreB, r2.ScoreB);
        Assert.Equal(r1.Stats.ShotsA, r2.Stats.ShotsA);
        Assert.Equal(r1.Stats.ShotsB, r2.Stats.ShotsB);
        Assert.Equal(r1.EventsFull.Count, r2.EventsFull.Count);
        Assert.Equal(r1.Stats.PossessionA, r2.Stats.PossessionA, 3);
        Assert.Equal(r1.Stats.PossessionB, r2.Stats.PossessionB, 3);
    }
}
