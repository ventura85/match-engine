using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using MatchEngine.Core.Domain.Teams.Presets;
using MatchEngine.Core.Engine.Commentary;
using MatchEngine.Core.Engine.Events;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using Xunit;

namespace MatchEngine.Tests.Engine;

public class CommentaryEventBucketTests
{
    private static readonly HashSet<EventType> Key = new()
    {
        EventType.Kickoff,
        EventType.Goal,
        EventType.SaveMade,
        EventType.ShotOnTarget,
        EventType.FreekickAwarded,
        EventType.CornerAwarded,
        EventType.FoulCommitted,
        EventType.YellowCard,
        EventType.RedCard,
        EventType.FinalWhistle,
    };

    [Fact]
    public void Descriptions_always_from_matching_event_bucket()
    {
        var repo = new JsonCommentRepository("assets/comments");
        var a = SeedData.Red_433_Attacking();
        var b = SeedData.Blue_4141_Balanced();

        // Collect from several seeds to hit variety
        var reports = new List<MatchEngine.Core.Reporting.MatchReport>();
        foreach (var seed in new[] { 7, 42, 101, 1234, 9090 })
        {
            reports.Add(new EngineMatch(a, b, seed).Simulate(90));
        }

        foreach (var r in reports)
        {
            foreach (var e in r.EventsFull.Where(x => Key.Contains(x.Type) && !string.IsNullOrWhiteSpace(x.Description)))
            {
                var name = EventCatalog.GetName((int)e.Type);
                var allowed = repo.Get("pl", "fun", name).Concat(repo.Get("pl", "neutral", name)).Distinct().ToList();
                allowed.Should().NotBeEmpty($"bucket for {name} should exist");

                // Instantiate placeholders for this event
                var opponent = e.Team == r.TeamA ? r.TeamB : (e.Team == r.TeamB ? r.TeamA : string.Empty);
                bool match = allowed.Any(t => Instantiate(t, e.Minute, e.Team, opponent) == e.Description);
                match.Should().BeTrue($"description must come from templates of event {name}");
            }
        }
    }

    private static string Instantiate(string template, int minute, string team, string opponent)
    {
        return template
            .Replace("{minute}", minute.ToString())
            .Replace("{team}", team ?? string.Empty)
            .Replace("{opponent}", opponent ?? string.Empty);
    }
}

