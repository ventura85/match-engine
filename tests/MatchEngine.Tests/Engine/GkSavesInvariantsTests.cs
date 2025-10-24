using System.Linq;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using MatchEngineType = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

public class GkSavesInvariantsTests
{
    [Fact]
    public void SavesPlusGoalsEqualShotsOnTarget_PerTeam()
    {
        var r = new MatchEngineType(SeedData.Red_433_Attacking(), SeedData.Blue_4141_Balanced(), 4242).Simulate(90);
        int savesA = r.EventsFull.Count(e => e.Type == EventType.SaveMade && e.Team == r.TeamA);
        int savesB = r.EventsFull.Count(e => e.Type == EventType.SaveMade && e.Team == r.TeamB);
        Assert.Equal(r.Stats.ShotsOnTargetA, r.Stats.GoalsA + savesB); // A attacks -> B saves
        Assert.Equal(r.Stats.ShotsOnTargetB, r.Stats.GoalsB + savesA);
    }
}

