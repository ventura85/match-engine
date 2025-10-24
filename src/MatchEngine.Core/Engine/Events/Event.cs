namespace MatchEngine.Core.Engine.Events;

public readonly record struct Event(int Minute, EventType Type, string Team, string? Description = null);
public readonly record struct Goal(int Minute, string Team, string Scorer, string? Assist = null);

