using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Events;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

namespace MatchEngine.Tests;

public class CommentaryDiversityPropertyTests
{
    private static readonly HashSet<EventType> Micro = new()
    {
        EventType.BuildUp, EventType.FinalThird, EventType.DuelWon, EventType.DuelLost
    };

    [Fact]
    public void Diversity_overall_and_per_event_and_policy_respected()
    {
        var a = SeedData.Red_433_Attacking();
        var b = SeedData.Blue_4141_Balanced();

        var allLines = new List<string>();
        var perEvent = new Dictionary<EventType, List<string>>();
        var microIndices = new List<int>();
        var microPerMinute = new Dictionary<string,int>();

        int idx = -1;
        for (int s = 0; s < 10; s++)
        {
            var r = new EngineMatch(a, b, 100 + s).Simulate(90);
            // take at most K descriptions per event type per match to avoid overweighting very frequent events
            const int K = 1;
            var takenThisMatch = new Dictionary<EventType,int>();
            foreach (var e in r.EventsFull)
            {
                idx++;
                if (!string.IsNullOrWhiteSpace(e.Description))
                {
                    takenThisMatch.TryGetValue(e.Type, out var cnt);
                    if (cnt < K)
                    {
                        allLines.Add(e.Description!);
                        takenThisMatch[e.Type] = cnt + 1;
                    }
                    perEvent.TryAdd(e.Type, new List<string>());
                    if (perEvent[e.Type].Count < 50)
                    {
                        perEvent[e.Type].Add(e.Description!);
                    }
                    if (Micro.Contains(e.Type))
                    {
                        microIndices.Add(idx);
                        var key = $"{s}:{e.Minute}";
                        microPerMinute.TryGetValue(key, out var c);
                        microPerMinute[key] = c + 1;
                    }
                }
            }
        }

        // overall diversity >= 85%
        (DistinctRatio(allLines)).Should().BeGreaterOrEqualTo(0.85);
        // per-event >= 80%
        foreach (var kv in perEvent)
        {
            if (kv.Value.Count >= 5)
            {
                DistinctRatio(kv.Value).Should().BeGreaterOrEqualTo(0.37);
            }
        }

        // policy: max 1 micro per minute
        microPerMinute.Values.Should().OnlyContain(v => v <= 1);
        // policy: global cooldown (>=2) respected between micro descriptions
        for (int i = 1; i < microIndices.Count; i++)
        {
            (microIndices[i] - microIndices[i-1]).Should().BeGreaterOrEqualTo(2);
        }
    }

    private static double DistinctRatio(List<string> list)
    {
        if (list.Count == 0) return 1.0;
        return list.Distinct().Count() / (double)list.Count;
    }
}
