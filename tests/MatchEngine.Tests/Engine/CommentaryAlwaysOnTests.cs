using System.Linq;
using FluentAssertions;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

namespace MatchEngine.Tests.Engine;

public class CommentaryAlwaysOnTests
{
    [Fact]
    public void Key_events_always_have_descriptions()
    {
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        var r = new EngineMatch(a, b, 4242).Simulate(90);
        var keys = new[] { EventType.Goal, EventType.SaveMade, EventType.ShotOnTarget, EventType.FinalWhistle, EventType.FreekickAwarded, EventType.CornerAwarded, EventType.Kickoff };
        foreach (var e in r.EventsFull.Where(x => keys.Contains(x.Type)))
        {
            e.Description.Should().NotBeNullOrWhiteSpace($"{e.Type} should always have commentary");
        }
    }
}

