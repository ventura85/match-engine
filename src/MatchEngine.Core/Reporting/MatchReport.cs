using System.Collections.Generic;
using MatchEngine.Core.Engine.Events;
using MatchEngine.Core.Engine.Stats;

namespace MatchEngine.Core.Reporting;

public sealed class MatchReport
{
    public required string TeamA { get; init; }
    public required string TeamB { get; init; }
    public int ScoreA { get; init; }
    public int ScoreB { get; init; }
    public required Stats Stats { get; init; }
    public List<Goal> Goals { get; } = new();
    public List<Event> Events { get; } = new();
    public List<Event> EventsFull { get; } = new();
    public int SchemaVersion { get; init; } = 1;
    public string? EventsNdjson { get; init; }
}

