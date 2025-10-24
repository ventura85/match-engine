using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using MatchEngineType = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

public class EventsMonotonicityTests
{
    [Fact]
    public void MinutesMonotonicAndFinalWhistleExists()
    {
        var r = new MatchEngineType(SeedData.Red_433_Attacking(), SeedData.Blue_4141_Balanced(), 777).Simulate(90);
        int prev = -1;
        foreach (var e in r.EventsFull)
        {
            Assert.True(e.Minute >= prev);
            prev = e.Minute;
        }
        Assert.Contains(r.EventsFull, x => x.Type == EventType.FinalWhistle);
    }
}
