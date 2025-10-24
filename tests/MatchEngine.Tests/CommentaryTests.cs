using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

namespace MatchEngine.Tests;

public class CommentaryTests
{
    private static readonly HashSet<EventType> KeyEvents = new()
    {
        EventType.Goal,
        EventType.SaveMade,
        EventType.ShotOnTarget,
        EventType.FreekickAwarded,
        EventType.CornerAwarded,
        EventType.FoulCommitted,
        EventType.YellowCard,
        EventType.RedCard,
        EventType.PenaltyAwarded,
        EventType.FinalWhistle,
        EventType.Kickoff,
    };

    [Fact]
    public void Determinism_same_seed_same_lines()
    {
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        var r1 = new EngineMatch(a, b, 2025).Simulate(90);
        var r2 = new EngineMatch(a, b, 2025).Simulate(90);
        var d1 = r1.EventsFull.Where(e => KeyEvents.Contains(e.Type)).Select(e => e.Description ?? "").ToArray();
        var d2 = r2.EventsFull.Where(e => KeyEvents.Contains(e.Type)).Select(e => e.Description ?? "").ToArray();
        d2.Should().Equal(d1);
    }

    [Fact]
    public void Diversity_at_least_80_percent()
    {
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        int seed = 1; List<string> lines = new();
        while (lines.Count < 30 && seed < 200)
        {
            var r = new EngineMatch(a, b, seed++).Simulate(90);
            lines.AddRange(r.EventsFull.Where(e => KeyEvents.Contains(e.Type)).Select(e => e.Description ?? ""));
        }
        lines.Count.Should().BeGreaterOrEqualTo(30);
        var unique = lines.Where(s => !string.IsNullOrWhiteSpace(s)).Distinct().Count();
        (unique / (double)lines.Count).Should().BeGreaterOrEqualTo(0.80);
    }

    [Fact]
    public void No_repeat_within_cooldown()
    {
        const int cooldown = 6; // should match composer default
        var a = SeedData.Red_433_Attacking(); var b = SeedData.Blue_4141_Balanced();
        var r = new EngineMatch(a, b, 9090).Simulate(90);
        var lines = r.EventsFull.Where(e => KeyEvents.Contains(e.Type)).Select(e => e.Description ?? "").ToList();
        for (int i = 0; i < lines.Count; i++)
        {
            var windowStart = Math.Max(0, i - cooldown + 1);
            var window = lines.Skip(windowStart).Take(cooldown).ToList();
            if (window.Count <= 1) continue;
            var dup = window.GroupBy(x => x).Where(g => !string.IsNullOrWhiteSpace(g.Key) && g.Count() > 1).Select(g => g.Key).FirstOrDefault();
            dup.Should().BeNull("no duplicate within cooldown window");
        }
    }
}

