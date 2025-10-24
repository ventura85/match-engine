using System.Linq;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using MatchEngineType = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

public class InvariantsTests
{
    [Fact]
    public void ShotsAndPossessionAndSetPiecesConsistent()
    {
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        var r = new MatchEngineType(a, b, 321).Simulate(90);
        Assert.True(r.Stats.GoalsA <= r.Stats.ShotsOnTargetA && r.Stats.ShotsOnTargetA <= r.Stats.ShotsA);
        Assert.True(r.Stats.GoalsB <= r.Stats.ShotsOnTargetB && r.Stats.ShotsOnTargetB <= r.Stats.ShotsB);
        var possSum = r.Stats.PossessionA + r.Stats.PossessionB;
        Assert.InRange(possSum, 99.5, 100.5);
        int fka = r.EventsFull.Count(e => e.Type == EventType.FreekickAwarded && e.Team == r.TeamA);
        int fkb = r.EventsFull.Count(e => e.Type == EventType.FreekickAwarded && e.Team == r.TeamB);
        int ca = r.EventsFull.Count(e => e.Type == EventType.CornerAwarded && e.Team == r.TeamA);
        int cb = r.EventsFull.Count(e => e.Type == EventType.CornerAwarded && e.Team == r.TeamB);
        Assert.Equal(fka, r.Stats.FreekicksA);
        Assert.Equal(fkb, r.Stats.FreekicksB);
        Assert.Equal(ca, r.Stats.CornersA);
        Assert.Equal(cb, r.Stats.CornersB);
    }
}
